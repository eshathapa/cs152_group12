import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
from gemini_detector import GeminiDoxxingDetector
import pdb
import count as count_tool
from queue import PriorityQueue
from itertools import count

# Set up logging to the console
logger = logging.getLogger('discord')
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    discord_token = tokens['discord']

class ModBot(discord.Client):
    def __init__(self): 
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='.', intents=intents)
        self.group_num = None
        self.mod_channels = {} # Map from guild to the mod channel id for that guild
        self.reports = {} # Map from user IDs to the state of their report
        self.reviews = {}
        self.reviewing_queue = PriorityQueue()
        self.unique = count()
        
        # AI: Initialize Gemini detector
        try:
            self.gemini_detector = GeminiDoxxingDetector(
                project_id=tokens['project_id'],
                location=tokens.get('google_location', 'us-central1')
            )
            print("🤖 Gemini AI doxxing detector loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize Gemini detector: {e}")
            print("📝 Bot will continue without AI analysis")
            self.gemini_detector = None

    async def on_ready(self):
        print(f"DEBUG: Bot name is '{self.user.name}'")

        print(f'{self.user.name} has connected to Discord! It is these guilds:')
        for guild in self.guilds:
            print(f' - {guild.name}')
        print('Press Ctrl-C to quit.')

        # Parse the group number out of the bot's name
        match = re.search('[gG]roup (\d+) [bB]ot', self.user.name)
        if match:
            self.group_num = match.group(1)
        else:
            raise Exception("Group number not found in bot's name. Name format should be \"Group # Bot\".")

        # Find the mod channel in each guild that this bot should report to
        for guild in self.guilds:
            for channel in guild.text_channels:
                if channel.name == f'group-{self.group_num}-mod':
                    self.mod_channels[guild.id] = channel
        

    async def on_message(self, message):
        '''
        This function is called whenever a message is sent in a channel that the bot can see (including DMs). 
        Currently the bot is configured to only handle messages that are sent over DMs or in your group's "group-#" channel. 
        '''
        print(f"📝 Received message from {message.author}: {message.content}")

        # Ignore messages from the bot
        if message.author.id == self.user.id:
            return

        # Check if this message was sent in a server ("guild") or if it's a DM
        if message.guild:
            await self.handle_channel_message(message)
        else:
            await self.handle_dm(message)

    async def handle_dm(self, message):
        # Handle a help message
        if message.content == Report.HELP_KEYWORD:
            reply =  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
            return

        # if message.content.startswith(Review.START_KEYWORD):
        if message.content == Review.HELP_KEYWORD and message.author.id not in self.reviews:
            reply =  "Type in the moderator password to begin the reviewing process.\n"
            await message.channel.send(reply)

        author_id = message.author.id
        responses = []

        # If the user's previous report is complete or cancelled, remove it from our map
        if author_id in self.reports and self.reports[author_id].report_complete():
            self.reports.pop(author_id)

        if author_id in self.reviews and self.reviews[author_id].review_complete():
            self.reviews.pop(author_id)

        if author_id not in self.reviews and message.content.startswith(Review.PASSWORD):
            self.reviews[author_id] = Review(self)

        if author_id in self.reviews:
            # Let the report class handle this message; forward all the messages it returns to us
            responses = await self.reviews[author_id].handle_message(message)
            for r in responses:
                await message.channel.send(r)
            return

        # Respond to messages if they're part of a reporting flow
        if author_id not in self.reports and not message.content.startswith(Report.START_KEYWORD):
            return

        # If we don't currently have an active report for this user, add one
        if author_id not in self.reports:
            self.reports[author_id] = Report(self)

        # Let the report class handle this message; forward all the messages it returns to uss
        responses = await self.reports[author_id].handle_message(message)
        for r in responses:
            await message.channel.send(r)

        # Add finalized report to queue to remove
        if author_id in self.reports and self.reports[author_id].report_complete():
            finalized_report = self.reports[author_id]
            if not finalized_report.cancelled:
                self.reviewing_queue.put((1 / finalized_report.get_report_score(), next(self.unique), finalized_report.full_report))
            self.reports.pop(author_id)

    async def handle_channel_message(self, message):
        # Only handle messages sent in the "group-#" channel or "group-#-mod" channel
        if message.channel.name == f'group-{self.group_num}-mod':
            if message.content == Review.HELP_KEYWORD:
                reply =  "Use the `review` command to begin the reviewing process.\n"
                await message.channel.send(reply)
                return

            # /count command under -mod channel
            if message.content.strip() == "/count":
                counts = count_tool.get_counts(message.guild.id)
                if not counts:
                    await message.channel.send("No harassment reports have been logged yet.")
                else:
                    # Build a readable report of counts
                    lines = ["**Harassment Report Counts:**"]
                    for user_id, num in counts.items():
                        member = message.guild.get_member(user_id)
                        name_display = member.display_name if member else f"User ID {user_id}"
                        lines.append(f"- {name_display} (`{user_id}`): {num}")
                    await message.channel.send("\n".join(lines))
                return

            # Only respond to messages if they're part of a reviewing flow
            if not message.content.startswith(Review.START_KEYWORD):
                return

            # Let the review class handle this message; forward all the messages it returns to uss
            responses = await Review(self).handle_message(message)
            for r in responses:
                await message.channel.send(r)

        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.name}: "{message.content}"')
        
        # Analyze for doxxing and take action
        analysis_result = await self.eval_text(message)
        
        # Only act if doxxing is detected
        if analysis_result.get('is_doxxing', False):
            # Send detailed analysis to mod channel
            formatted_analysis = self.code_format(analysis_result)
            await mod_channel.send(formatted_analysis)
            
            # DELETE the original message and send user notification
            try:
                # Get the info types that were detected
                info_disclosed = analysis_result.get('information_disclosed', {})
                info_types = info_disclosed.get('info_types_found', [])
                
                # Create a user-friendly list of what was detected
                detected_info = []
                type_mapping = {
                    'phone': 'phone number',
                    'email': 'email address', 
                    'address': 'address',
                    'real_name': 'personal name',
                    'financial': 'financial information',
                    'government_id': 'ID information',
                    'social_media': 'social media account',
                    'workplace': 'workplace information'
                }
                
                for info_type in info_types:
                    if info_type in type_mapping:
                        detected_info.append(type_mapping[info_type])
                    else:
                        detected_info.append(info_type.replace('_', ' '))
                
                # Format the detected info nicely
                if len(detected_info) == 1:
                    info_text = detected_info[0]
                elif len(detected_info) == 2:
                    info_text = f"{detected_info[0]} and {detected_info[1]}"
                else:
                    info_text = f"{', '.join(detected_info[:-1])}, and {detected_info[-1]}"
                
                # Delete the original message
                await message.delete()
                
                # Send user notification
                user_message = f"🛡️ {message.author.mention}, your message was removed because it may contain personal information"
                if detected_info:
                    user_message += f" ({info_text})"
                user_message += ". Please avoid sharing others' private information to protect their privacy and safety."
                
                await message.channel.send(user_message)
                
                # Log successful deletion to mod channel
                await mod_channel.send(f"✅ **Automatic Action Taken:** Message deleted and user notified.")
                
            except discord.Forbidden:
                # Bot doesn't have permission to delete messages
                await mod_channel.send(f"❌ **Permission Error:** Cannot delete messages. Please check bot permissions.")
            except discord.NotFound:
                # Message was already deleted
                await mod_channel.send(f"⚠️ **Note:** Message was already deleted.")
            except Exception as e:
                # Other error occurred
                await mod_channel.send(f"❌ **Error:** Failed to delete message: {str(e)}")
    
    async def eval_text(self, message):
        if not self.gemini_detector:
            return {
                'is_doxxing': False,
                'confidence': 0.0,
                'reasoning': 'AI detector not available',
                'original_message': message.content,
                'author': message.author.display_name
            }
        
        try:
            # Use Gemini to analyze the message
            analysis = self.gemini_detector.analyze_for_doxxing(
                message_content=message.content,
                author_name=message.author.display_name
            )
            
            # Add original message for reference
            analysis['original_message'] = message.content
            analysis['author'] = message.author.display_name
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error during AI analysis: {e}")
            return {
                'is_doxxing': False,
                'confidence': 0.0,
                'reasoning': f'Analysis error: {str(e)}',
                'original_message': message.content,
                'author': message.author.display_name
            }

    
    def code_format(self, analysis):
        '''
        Format the AI analysis results for doxxing detection only
        '''
        # This method now only gets called when doxxing is detected
        author = analysis.get('author', 'Unknown')
        original_message = analysis.get('original_message', 'N/A')
        
        # Use the detailed formatter for doxxing cases
        detailed_report = self.gemini_detector.format_detailed_report(analysis)
        if detailed_report:
            result = detailed_report
            result += f"\n\n**Original Message:** `{original_message}`"
        else:
            # Fallback if detailed formatter fails
            confidence = analysis.get('confidence', 0.0)
            mod_summary = analysis.get('moderator_summary', {})
            reasoning = mod_summary.get('reasoning', 'No reasoning provided')
            
            result = f"🚨 **DOXXING DETECTED**\n"
            result += f"**Author:** {author}\n"
            result += f"**Confidence:** {confidence:.0%}\n"
            result += f"**AI Reasoning:** {reasoning}\n"
            result += f"**Original Message:** `{original_message}`"
        
        return result

client = ModBot()
client.run(discord_token)

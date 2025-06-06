# bot.py
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
# from gemini_detector import GeminiDoxxingDetector, ProcessingGeminiResponse
from claude_detector import ClaudeDoxxingDetector, ProcessingClaudeResponse
import pdb
import count as count_tool
from queue import PriorityQueue
from itertools import count
from datetime import datetime
import json
from supabase_helper import insert_victim_log, insert_perpetrator_log, get_perpetrator_score

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
        self.unique = count(1)
        self.ai_reports = {} # Map from report counts to AI detailed reports
        self.warned = set()
        
        # AI: Initialize Gemini detector
        # try:
        #     self.gemini_detector = GeminiDoxxingDetector(
        #         project_id=tokens['project_id'],
        #         location=tokens.get('google_location', 'us-central1')
        #     )
        #     print("🤖 Gemini AI doxxing detector loaded successfully!")
        # except Exception as e:
        #     print(f"❌ Failed to initialize Gemini detector: {e}")
        #     print("📝 Bot will continue without AI analysis")
        #     self.gemini_detector = None
        try:
            self.gemini_detector = ClaudeDoxxingDetector()
            print("🤖 Claude AI doxxing detector loaded successfully!")
        except Exception as e:
            print(f"❌ Failed to initialize Claude detector: {e}")
            print("📝 Bot will continue without AI analysis")
            self.gemini_detector = None

    async def on_ready(self):
        # print(f"DEBUG: Bot name is '{self.user.name}'")

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
            reply =  "I don't know what that command means.\n"
            reply +=  "Use the `report` command to begin the reporting process.\n"
            reply += "Use the `cancel` command to cancel the report process.\n"
            await message.channel.send(reply)
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
                reply =  "To review a report, please DM the bot (that's me!) with the password. Reviewing is done via DM to prevent congestion in the shared moderator channel.\n"
                await message.channel.send(reply)
                return

        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel (COMMENTED OUT)
        mod_channel = self.mod_channels[message.guild.id]
        # await mod_channel.send(f'Forwarded message:\n{message.author.mention}: "{message.content}"\n[Click to View Message]({message.jump_url})')
        
        # Analyze for doxxing and take action
        analysis_result = await self.eval_text(message)
        await self.react_to_message(analysis_result, message, mod_channel)

        return
    
    async def eval_text(self, message):
        """
        Runs AI bot on message sent in general channel. Returns analysis.
        """
        if not self.gemini_detector:
            return {
                'is_doxxing': False,
                'probability_of_doxxing': 0.0,
                'confidence': 0.0,  # Backward compatibility
                'reasoning': 'AI detector not available',
                'original_message': message.content,
                'author': message.author.mention
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
            
            # Ensure probability_of_doxxing is between 0 and 1
            if 'probability_of_doxxing' in analysis:
                analysis['probability_of_doxxing'] = max(0.0, min(1.0, float(analysis['probability_of_doxxing'])))
            # Also support old confidence field for backward compatibility
            if 'confidence' in analysis:
                analysis['confidence'] = max(0.0, min(1.0, float(analysis['confidence'])))
            
            # DEBUG: Show full analysis data
            # print(f"🎯 FULL ANALYSIS DATA: {analysis}")
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error during AI analysis: {e}")
            return {
                'is_doxxing': False,
                'probability_of_doxxing': 0.0,
                'confidence': 0.0,  # Backward compatibility
                'reasoning': f'Analysis error: {str(e)}',
                'original_message': message.content,
                'author': message.author.mention
            }

    async def react_to_message(self, analysis, message, mod_channel):
        """
        Takes action based on the response from the bot.
        """
        # Only act if doxxing is detected
        if analysis.get('is_doxxing', False):
            formatter = ProcessingClaudeResponse(analysis, message)
            embed, bot_report, risk, confidence, doxxing_score = formatter.format_bot_response()
            
            # Take action based on probability level
            try:
                # Low probability -> No action, no report
                if confidence < 0.5:
                    return
                
                # At least 50% probability: add detailed report to dictionary
                report_number = next(self.unique)
                self.ai_reports[report_number] = bot_report

                # Probability over 84%: delete message, notify and warn offender
                if confidence > 0.7:
                    # Get the info types that were detected
                    info_disclosed = analysis.get('information_disclosed', {})
                    info_types = info_disclosed.get('info_types_found', [])
                    
                    # Extract victim name for logging
                    target_info = analysis.get('target_analysis', {})
                    victim_name = target_info.get('who_was_doxxed', 'Unknown')
                    
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
                    print(detected_info)
                    if len(detected_info) == 1:
                        info_text = detected_info[0]
                    elif len(detected_info) == 2:
                        info_text = f"{detected_info[0]} and {detected_info[1]}"
                    elif len(detected_info) > 0:
                        info_text = f"{', '.join(detected_info[:-1])}, and {detected_info[-1]}"
                    else:
                        info_text = ""

                    # Delete the original message
                    await message.delete()
                    
                    # Log to Supabase: victim and perpetrator
                    if victim_name and victim_name != "Unknown":
                        insert_victim_log(victim_name, datetime.now())
                    insert_perpetrator_log(str(message.author.id), message.author.display_name, datetime.now(), victim_name, risk)

                    perp_score = get_perpetrator_score(str(message.author.id))
                    
                    # Send warning message in the SAME CHANNEL where the message was posted
                    channel_message = "🛡️ A post was automatically removed for containing personally identifiable information. Please do not post other people's personally identifiable information on our platform."
                    await message.channel.send(channel_message)

                    # Send specific DM to offender
                    user_message = f"🛡️ {message.author.mention}, a message you recently sent was removed because it was flagged as containing personal information"
                    if len(detected_info) > 0:
                        user_message += f" ({info_text})"
                    user_message += f".\nPlease avoid sharing others' private information to protect their privacy and safety. Future offenses may result in action taken against your account."
                    await message.author.send(user_message)

                    # Check for consequences based on harassment count
                    if perp_score < 3 and author.id in self.warned:
                        self.warned.remove(author.id)
                    if perp_score >= 3 and perp_score < 5:
                        # Send warning card to channel
                        warning_embed = discord.Embed(
                            title="**Official Warning**",
                            color=0xf1c40f,  # Yellow
                            timestamp=datetime.now()
                        )
                        warning_embed.add_field(name="**User**", value=f"{message.author.mention} (`{message.author.display_name}`, ID: `{message.author.id}`)", inline=False)
                        warning_embed.add_field(name="**Action**", value="**Warning Issued**", inline=True)
                        warning_embed.add_field(name="**Reason**", value="Multiple or severe doxxing violations detected by automated system", inline=True)
                        warning_embed.add_field(name="**Notice**", value="Continued violations may result in suspension. Please review community guidelines.", inline=False)
                        warning_embed.set_footer(text="Automated Moderation System")
                        
                        await message.author.send(embed=warning_embed)
                        await mod_channel.send(f"User {message.author.mention} was sent a warning.")
                        self.warned.add(message.author.id)
                        
                    elif perp_score >= 5 and perp_score < 10:
                        # Send suspension notification card to channel
                        suspension_embed = discord.Embed(
                            title="**Suspension Notice**",
                            color=0xe74c3c,  # Red
                            timestamp=datetime.now()
                        )
                        suspension_embed.add_field(name="**User**", value=f"{message.author.mention} (`{message.author.display_name}`, ID: `{message.author.id}`)", inline=False)
                        suspension_embed.add_field(name="**Action**", value="**Suspension Issued**", inline=True)
                        suspension_embed.add_field(name="**Reason**", value="Persistent doxxing violations detected by automated system", inline=True)
                        suspension_embed.add_field(name="**Note**", value="**This is a demonstration.** In a live environment, this account would have user privileges restricted for three (3) days. Future offenses may result in further account action.", inline=False)
                        suspension_embed.set_footer(text="Automated Moderation System")
                        
                        await message.author.send(embed=suspension_embed)
                        await mod_channel.send(f"User {message.author.mention} was suspended for three (3) days.")
                        self.warned.add(message.author.id)
                    
                    elif perp_score > 10:
                        # Send suspension notification card to channel
                        suspension_embed = discord.Embed(
                            title="**Account Banned Notice**",
                            color=0xe74c3c,  # Red
                            timestamp=datetime.now()
                        )
                        suspension_embed.add_field(name="**User**", value=f"{message.author.mention} (`{message.author.display_name}`, ID: `{message.author.id}`)", inline=False)
                        suspension_embed.add_field(name="**Action**", value="**Ban Issued**", inline=True)
                        suspension_embed.add_field(name="**Reason**", value="Persistent doxxing violations detected by automated system after suspension", inline=True)
                        suspension_embed.add_field(name="**Note**", value="**This is a demonstration.** In a live environment, this account would be banned from the platform.", inline=False)
                        suspension_embed.set_footer(text="Automated Moderation System")
                        
                        await message.author.send(embed=suspension_embed)
                        await mod_channel.send(f"User {message.author.mention} was banned from the platform.")
                        self.warned.add(message.author.id)
                

                # 50-84% probability: add report to manual review queue
                else:
                    # Same priority calculation as in report.py
                    priority = 0
                    if doxxing_score == 0 or risk == 0:
                        priority = doxxing_score + risk
                    else:
                        priority = doxxing_score * risk
                    self.reviewing_queue.put((1 / priority, report_number, embed))
                                    
                # Log bot evaluation to moderator channel
                embed.add_field(name="📝 **Original Message**", value=f"```{message.content[:1000]}```" + ("... (truncated)" if len(message.content) > 1000 else ""), inline=False)
                embed.set_footer(text=f"Evaluated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}.")
                
                await mod_channel.send(embed=embed)
                
                # Send -d message for ALL cases (both auto-deleted and manual review)
                await mod_channel.send(f"To view the details for this decision, DM the bot `-d {report_number}`")

            except discord.Forbidden:
                # Bot doesn't have permission to delete messages
                await mod_channel.send(f"❌ **Permission Error:** Cannot delete messages. Please check bot permissions.")
            except discord.NotFound:
                # Message was already deleted
                await mod_channel.send(f"⚠️ **Note:** Message was already deleted.")
            except Exception as e:
                # Other error occurred
                await mod_channel.send(f"❌ **Error:** Tried to but failed to delete message: {str(e)}")

        return

client = ModBot()
client.run(discord_token)
import discord
from discord.ext import commands
import os
import json
import logging
import re
import requests
from report import Report
from review import Review
from gemini_detector import GeminiDoxxingDetector, ProcessingGeminiResponse
import pdb
import count as count_tool
from queue import PriorityQueue
from itertools import count
from datetime import datetime
import json

# FOR TESTING WITHOUT USING CREDITS (see lines 213-215)
TEST_STRING = '''{ "is_doxxing": false,
    "confidence": 0.48,
    "risk_level": "MEDIUM",
    "target_analysis": {
        "who_was_doxxed": "TestVictim",
        "relationship_to_author": "stranger",
        "is_public_figure": false,
        "apparent_consent": "none" },
    "information_disclosed": {
        "info_types_found": ["real_name", "address"],
        "specificity_level": "approximate",
        "sensitive_details": ["address: 123 main street"],
        "partial_info": "" },
    "context_analysis": {
        "apparent_intent": "malicious",
        "conversation_tone": "casual",
        "potential_harm_level": "immediate",
        "escalation_indicators": ["threat"] },
    "moderator_summary": {
        "primary_concern": "Sharing a potentially private address without consent could lead to harassment or stalking.",
        "immediate_risks": [],
        "reasoning": "The message provides an address: 'crothers e445'. Without further context, it's unclear what type of address this is (house, apartment, PO box etc.). However, addresses, in general, are considered private information, and sharing it without consent is a common form of doxxing. Because we lack context, it's difficult to determine the sender's intent. The exact location provided warrants a high level of concern due to the potential for immediate harm. If this is a home address, the target could be directly targeted, making it high risk. If it is something else, it might not be. This uncertainty accounts for a confidence score of 0.85.",
        "recommended_action": "remove immediately",
        "follow_up_needed": "" }
    }'''

TEST_JSON=json.loads(TEST_STRING)

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
        self.ai_reports = {} # Map from report counts to AI detailed reports
        
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
        # print(f"📝 Received message from {message.author}: {message.content}")

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

        if not message.channel.name == f'group-{self.group_num}':
            return

        # Forward the message to the mod channel
        mod_channel = self.mod_channels[message.guild.id]
        await mod_channel.send(f'Forwarded message:\n{message.author.mention}: "{message.content}"\n[Click to View Message]({message.jump_url})')
        
        # Analyze for doxxing and take action
        # SWAP WHICH ONE IS COMMENTED OUT IF YOU WANT TO CHANGE BETWEEN HARD-CODED AI RESPONSE AND LIVE AI BOT
        # analysis_result = await self.eval_text(message)
        analysis_result = TEST_JSON

        await self.react_to_message(analysis_result, message, mod_channel)

        return
    
    async def eval_text(self, message):
        """
        Runs AI bot on message sent in general channel. Returns analysis.
        """
        if not self.gemini_detector:
            return {
                'is_doxxing': False,
                'confidence': 0.0,
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
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error during AI analysis: {e}")
            return {
                'is_doxxing': False,
                'confidence': 0.0,
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
            formatter = ProcessingGeminiResponse(analysis, message)
            embed, bot_report, risk, confidence, doxxing_score = formatter.format_bot_response()
            
            # Take action based on confidence level
            try:
                # Low confidence -> No action, no report
                if confidence < 0.5:
                    return
                
                # At least 50% confidence: add detailed report to dictionary of when bot identified doxxing
                report_number = next(self.unique)
                self.ai_reports[report_number] = bot_report

                # Confidence over 84%: delete message, notify and warn offender
                if confidence > 0.84:
                    # Get the info types that were detected
                    info_disclosed = analysis.get('information_disclosed', {})
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

                    original_content = f"```{message.content[:1000]}```" + ("... (truncated)" if len(message.content) > 1000 else "")

                    # Delete the original message
                    await message.delete()
                    
                    # Send offender DM
                    user_message = f"🛡️ {message.author.mention}, your message was removed because it it was flagged as containing personal information"
                    if detected_info:
                        user_message += f" ({info_text})"
                    user_message += f".\n{original_content}\nPlease avoid sharing others' private information to protect their privacy and safety. Future offenses may result in action taken against your account."
                    
                    await message.author.send(user_message)

                # 50-84% confidence: add report to manual review queue
                else:
                    # Same priority calculation as in report.py
                    priority = 0
                    if doxxing_score == 0 or risk == 0:
                        priority = doxxing_score + risk
                    else:
                        priority = doxxing_score * risk
                    self.reviewing_queue.put((1 / priority, report_number, embed))
                                    
                # Log bot evaluation to moderator channel
                embed.add_field(name="**Evaluation ID**", value=report_number, inline=True)
                embed.set_footer(text=f"Evaluated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}.")
                await mod_channel.send(embed=embed)
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

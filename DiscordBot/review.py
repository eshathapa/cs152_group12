# review.py
from enum import Enum, auto
import discord
import re
import asyncio
from datetime import datetime, timedelta
from supabase_helper import insert_victim_log, insert_perpetrator_log, get_perpetrator_score
from dataclasses import dataclass, field
from typing import Any

class InfoType(Enum):
    CONTACT = "Contact Information"
    LOCATION = "Location Information"
    FINANCIAL = "Financial Information"
    ID = "ID Information"
    EXPLICIT = "Explicit Content"
    OTHER = "Other"

class State(Enum):
    REVIEW_START = auto()
    AWAITING_THREAT_JUDGEMENT = auto()
    AWAITING_OTHER_ABUSE_JUDGEMENT = auto()
    AWAITING_DISALLOWED_INFO = auto()
    AWAITING_CONTENT_CHECK = auto()
    AWAITING_INTENTION = auto()
    CONFIRMING_REVIEW = auto()
    REVIEW_COMPLETE = auto()
    AWAITING_FAITH_INDICATOR = auto()
    AWAITING_NAME = auto()
    NAME_CONFIRMATION = auto()
    AWAITING_CONTINUE = auto()
    

class Review:
    PASSWORD = "modpassword"
    CANCEL_KEYWORD = "-l"
    HELP_KEYWORD = "-h"
    POLICY_KEYWORD = "-p"
    DETAILS_KEYWORD = "-d"
    REVIEW_KEYWORD = "-r"

    
    def __init__(self, client):
        self.state = State.REVIEW_START
        self.client = client

        # Shared variables
        self.reports = client.reviewing_queue
        self.ai_reports = client.ai_reports
        self.warned = client.warned
        self.mod_channel = None

        # Variables specific to report info
        self.report = None
        self.priority = None
        self.id = None
        self.info_types = []
        self.timestamp = None
        self.victim_name = None
        self.guild_id = None
        self.reporter = None
        
        # Assessment flags set by the reviewer for building a summary
        self.threat_identified_by_reviewer = False
        self.disallowed_info_identified = False 
        self.other_pii_identified = False 

        # Flag to indicate if the original reported message should be deleted, suspended, permanently banned, and to escalate to a secondary reviewer
        self.remove = False
        self.suspend_user = False
        self.ban_user = False 
        self.risk_level = 1
        self.report_risk_level = None

        # Stored Discord objects for performing moderation actions- these are fetched based on information in the report_details embed
        self.original_reported_message = None 
        self.abuse_type = None

    async def handle_message(self, message: discord.Message):
        '''
        This function handles the reporting flow by managing state transitions
        and prompts at each state.
        '''

        # Review aborted. If a report was pulled, add back to queue.
        if message.content.lower() == self.CANCEL_KEYWORD:
            reply = "You are now logged out."
            self.state = State.REVIEW_COMPLETE
            if self.report:
                reply += " The review you had in progress has been cancelled."
                self.reports.put((self.priority, self.id, self.report))
            reply += " Type the password to begin again."
            return [reply]
        
        # Send help message
        if message.content.lower() == self.HELP_KEYWORD:
            return [self.get_help_message()]

        if message.content.lower() == self.POLICY_KEYWORD:
            return ["This is a placeholder for the doxxing policy."]
        
        if message.content.split(" ")[0].lower() == self.DETAILS_KEYWORD:
            tokens = message.content.split(" ")
            if len(tokens) > 1:
                evaluation_id = int(message.content.split(" ")[1])
                if evaluation_id in self.ai_reports:
                    return [self.ai_reports[evaluation_id]]
                return ["There is no bot report associated with that evaluation ID"]
            return[f"You must indicate an evaluation ID when requesting details in the form `{self.DETAILS_KEYWORD} [Evaluation ID]`"]
            
        # Start of review. Confirming moderator would like to continue.
        if self.state == State.REVIEW_START:
            self.timestamp = datetime.now()
            reply = "Thank you for starting the reviewing process. "
            reply += "At any time, you may do the following:\n"
            reply += f"- Type `{self.HELP_KEYWORD}` to see a help message.\n"
            reply += f"- Type `{self.CANCEL_KEYWORD}` to log out of the review bot. This will cancel any in-progress reviews.\n"
            reply += f"- Type `{self.DETAILS_KEYWORD} [Evaluation ID]` to review a bot's doxxing evaluation.\n"
            reply += f"- Type `{self.POLICY_KEYWORD}` to read our doxxing policy.\n"
            reply += f"To begin a review, type `{self.REVIEW_KEYWORD}`\n"
            self.state = State.AWAITING_CONTINUE
            return [reply]
        
        # Continuing with review. Pulling report from queue.
        if self.state == State.AWAITING_CONTINUE:
            if message.content.lower().strip() == self.REVIEW_KEYWORD:
                await message.author.send("Searching for reports...")
                # Loops over PQ to find a report with a valid message to review
                while not self.reports.empty():
                    try:
                        valid_message = False
                        full_entry = self.reports.get(block=True, timeout=5)
                        self.report = full_entry[2]
                        self.priority = full_entry[0]
                        self.id = full_entry[1]
                        # Populate variables with report details
                        for field in self.report.fields:

                            # Examine link associated with report to ensure message still exists
                            if field.name == "**Direct Link to Reported Message**": 
                                match = re.search(r'\((.*?)\)', field.value)
                                m = re.search(r'/(\d+)/(\d+)/(\d+)', match.group(1))
                                if m:
                                    self.guild_id, channel_id, message_id = map(int, m.groups())
                                    try:
                                        self.original_reported_message = await self.client.get_guild(self.guild_id).get_channel(channel_id).fetch_message(message_id)
                                        valid_message = True
                                    # Message was already deleted - program will move on to examine the next report without putting this back in the queue
                                    except discord.errors.NotFound:
                                        self.mod_channel = self.client.mod_channels.get(self.guild_id)
                                        if mod_channel:
                                            await self.mod_channel.send("A report was removed from the queue due to the post being deleted.")

                            # Get reporter name to send updates once review is completed (non-bot reports only)
                            if field.name == "**Filed By (Reporter)**":
                                reporter = field.value
                                if reporter != "MODERATOR BOT":
                                    m = re.search(r'\d+', reporter)
                                    self.reporter = await self.client.fetch_user(m[0])
                            if field.name == "**Risk Level**":
                                self.report_risk_level = int(field.value)
                            
                            # Store other report-specific variables
                            if field.name == "**Specific Reason Provided by Reporter**":
                                self.abuse_type = field.value
                            if field.name == "**Victim Name**":
                                self.victim_name = field.value
                        if not valid_message:
                            self.abuse_type = None
                            self.victim_name = None
                            self.reporter = None
                            self.guild_id = None
                            self.original_reported_message = None
                            continue

                        # Valid report found; continue to ask about threats
                        await message.author.send(embed=self.report)

                        # Ask about threats if it won't be redundant to asking about the abuse type itself
                        if self.abuse_type != "Credible Threat of Violence":
                            self.state = State.AWAITING_THREAT_JUDGEMENT
                            reply = "Here is the report to review. Please answer the following reporting flow questions.\n\n"
                            reply += "Does the post in question contain a threat?\n"
                            reply += "1. Yes, this post contains a threat.\n"
                            reply += "2. No, this post does not contain a threat."
                            return [reply]

                        # For "Credible Threat of Violence" only
                        self.state = State.AWAITING_OTHER_ABUSE_JUDGEMENT
                        reply = f"This message was flagged for {self.abuse_type.lower()}.\nDoes the post in question meet that criteria?\n"
                        reply += f"1. Yes, this post contains {self.abuse_type.lower()}.\n"
                        reply += f"2. No, this post does not contain {self.abuse_type.lower()}."
                        return [reply]

                    # Race condition - PQ exhausted
                    except Exception as e:
                        reply = "All reports have been reviewed or are currently under review.\n"
                        reply += "You may do any of the following:\n"
                        reply += f"- Type `{self.HELP_KEYWORD}` to see a help message.\n"
                        reply += f"- Type `{self.CANCEL_KEYWORD}` to log out of the review bot. This will cancel any in-progress reviews.\n"
                        reply += f"- Type `{self.DETAILS_KEYWORD} [Evaluation ID]` to review a bot's doxxing evaluation.\n"
                        reply += f"- Type `{self.POLICY_KEYWORD}` to read our doxxing policy.\n"
                        reply += f"You may attempt to review a report by typing `{self.REVIEW_KEYWORD}`. We recommend logging out using `{self.CANCEL_KEYWORD}` and check back again later instead of immediately attempting again."
                        return [reply]
                
                # No report in PQ to review
                reply = "All reports have been reviewed or are currently under review.\n"
                reply += "You may do any of the following:\n"
                reply += f"- Type `{self.HELP_KEYWORD}` to see a help message.\n"
                reply += f"- Type `{self.CANCEL_KEYWORD}` to log out of the review bot. This will cancel any in-progress reviews.\n"
                reply += f"- Type `{self.DETAILS_KEYWORD} [Evaluation ID]` to review a bot's doxxing evaluation.\n"
                reply += f"- Type `{self.POLICY_KEYWORD}` to read our doxxing policy.\n"
                reply += f"You may attempt to review a report by typing `{self.REVIEW_KEYWORD}`. We recommend logging out using `{self.CANCEL_KEYWORD}` and check back again later instead of immediately attempting again."
                return [reply]
            else:
                return [f"Please type one of the following: `{self.HELP_KEYWORD}`, `{self.CANCEL_KEYWORD}`, `{self.DETAILS_KEYWORD} [Evaluation ID]`, `{self.POLICY_KEYWORD}`, or `{self.REVIEW_KEYWORD}`"]
        
        # Updates variables based on threat assessment; asks for abuse assessment
        elif self.state == State.AWAITING_THREAT_JUDGEMENT:
            if message.content == "1":
                self.threat_identified_by_reviewer = True
                self.remove = True
                self.risk_level = 4
                # self.suspend_user = True
            elif message.content == "2": 
                self.threat_identified_by_reviewer = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            
            # Separate flow for doxxing - check for gov/financial info
            if self.abuse_type == "Doxxing":
                self.state = State.AWAITING_DISALLOWED_INFO
                reply = ("Our platform **never** allows government identification information (e.g. social security numbers) or financial information (e.g. bank account numbers, credit card numbers) to be posted.\n\n Does the post contain any of the **expressly disallowed information** listed above?\n1. Yes, it does.\n2. No, it does not.")
                return [reply]
            else:
                self.state = State.AWAITING_OTHER_ABUSE_JUDGEMENT
                reply = f"This message was flagged for {self.abuse_type.lower()}.\nDoes the post in question meet that criteria?\n"
                reply += f"1. Yes, this post contains {self.abuse_type.lower()}.\n"
                reply += f"2. No, this post does **not** contain {self.abuse_type.lower()}."
                return [reply]
            
        # Assessment for non-doxxing abuses
        elif self.state == State.AWAITING_OTHER_ABUSE_JUDGEMENT:
            if message.content == "1": 
                self.remove = True
                self.risk_level = self.report_risk_level
                # Threat variables were not set earlier for "Credible Threat of Violence" (to remove redundancy) - needs to be done here
                if self.abuse_type == "Credible Threat of Violence":
                    self.threat_identified_by_reviewer = True
                    # self.suspend_user = True

            # Confirmation message for non-doxxing review confirmation
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                    self.state = State.CONFIRMING_REVIEW
                    reply = ("Threat identified. Policy: Message removal & action against account.\n\n" 
                            "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                reply = ("Review assessment (no direct threat ID'd by you):\n")
                if self.remove:
                    reply += f"- {self.abuse_type} content was identified.\n"
                    reply += "- This will be logged. The post will be removed.\n"
                else: 
                    reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
                
        # DOXXING-SPECIFIC: log presence of gov info, financial info
        elif self.state == State.AWAITING_DISALLOWED_INFO:
            if message.content == "1":
                # Disallowed info present
                self.disallowed_info_identified = True
                self.remove = True
                # self.suspend_user = True
                self.risk_level += 2
            elif message.content == "2":
                self.disallowed_info_identified = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]

            # Ask about other PII
            self.state = State.AWAITING_CONTENT_CHECK
            reply = ("Does it contain **other personally identifiable information** (phone, email, location, employer)?\n1. Yes\n2. No")
            return [reply]
        
        # DOXXING-SPECIFIC: Moderator assesses whether PII is present
        elif self.state == State.AWAITING_CONTENT_CHECK:
            if message.content == "1":
                # Other PII is present: need to assess intention of post
                self.state = State.AWAITING_FAITH_INDICATOR
                response = ("""Was this post:
- Shared by the potentially targeted individual AND exhibits **clear** good faith
- Shared by someone who knows the potentially targeted individual AND exhibits **clear** good faith
- Shared to publicize a business or organization
If you are unsure, click on the message link to view the message in context before returning to this review.
1. Yes, meets at least one of the above criteria.
2. No, the post does not meet any of the above criteria.""")
                return [response]
            elif message.content == "2":
                self.other_pii_identified = False
            else:
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            
            # No malicious actor found, have user confirm review
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                 self.state = State.CONFIRMING_REVIEW
                 reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                reply = ("Review assessment (no direct threat ID'd by you):\n")
                if self.disallowed_info_identified:
                    reply += "- Severe personally identifiable information was identified. This post will be removed, and the user will be suspended.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                elif self.remove:
                    reply += "- Personally identifiable information was identified. This post will be removed.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                else: 
                    reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]

        # DOXXING-SPECIFIC: Moderator reports author intentions
        elif self.state == State.AWAITING_FAITH_INDICATOR:
            if message.content == "2":
                self.other_pii_identified = True # Only set if PII posted in bad context
                self.remove = True

                # Insert victim log into Doxxing Supabase (if victim name provided)
                if self.victim_name:
                    self.state = State.NAME_CONFIRMATION
                    reply = f"The victim name reported is `{self.victim_name}`. Please confirm that this is the correct name.\n"
                    reply += "1. This name is **correct**.\n"
                    reply += "2. This name is **incorrect**."
                    return[reply]
                else:
                    # Ask moderator to manually enter victim name
                    self.state = State.AWAITING_NAME
                    reply = "There is no victim name attached to this report. Please type the full name of the person being doxxed so the incident is accurately stored in our database. If you cannot tell the real name of the victim, type `Unknown`"
                    return [reply]
    
            elif message.content != "1":
                return ["Invalid input. Please type 1 for Yes or 2 for No."]
            
            # No malicious intent reported; confirm review.
            self.state = State.CONFIRMING_REVIEW
            if self.threat_identified_by_reviewer:
                self.state = State.CONFIRMING_REVIEW
                reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else: 
                reply = ("Review assessment (no direct threat ID'd by you):\n")
                if self.disallowed_info_identified:
                    reply += "- Severe personally identifiable information was identified. This post will be removed, and the user will be suspended.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                elif self.remove:
                    reply += "- Personally identifiable information was identified. This post will be removed.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                else: 
                    reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
        
        # DOXXING-SPECIFIC: Moderator indicates whether name on file is correct
        elif self.state == State.NAME_CONFIRMATION:
            # Name is wrong; put new name on file.
            if message.content == "2":
                self.state = State.AWAITING_NAME
                reply = "Please type the name of the person being doxxed below:"
                return[reply]
            elif message.content != "1":
                reply = f"Please type `1` if {self.victim_name} is the correct name and `2` if incorrect."
                return [reply]
            
            # Name is correct; confirm review.
            self.state = State.CONFIRMING_REVIEW
            
            # If threat: different review outcome
            if self.threat_identified_by_reviewer:
                 self.state = State.CONFIRMING_REVIEW
                 reply = ("Threat identified. Policy: Message removal & 1-day user suspension.\n\n" 
                          "Confirm review and actions?\n1. Yes (Proceed)\n2. No (Cancel Review)")
            else:
                # No threat assessed: typical review outcome
                reply = ("Review assessment (no direct threat ID'd by you):\n")
                if self.disallowed_info_identified:
                    reply += "- Severe personally identifiable information was identified. This post will be removed, and the user will be suspended.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                elif self.remove:
                    reply += "- Personally identifiable information was identified. This post will be removed.\n"
                    reply += "- This will be logged. Manual moderator follow-up may be appropriate.\n"
                else: 
                    reply += "- No direct threat or other significant problematic content was flagged by you.\n"
                reply += "No suspension will occur (policy requires reviewer to ID direct threat).\n\n"
                reply += "Finalize and log assessment?\n1. Yes (Finalize)\n2. No (Cancel Review)"
            return [reply]
            
        # DOXXING-SPECIFIC: Moderator types in victim name
        elif self.state == State.AWAITING_NAME:
            self.victim_name = message.content
            self.state = State.NAME_CONFIRMATION
            reply = f"The name now on file is `{self.victim_name}`. Is this correct?\n"
            reply += "1. Yes, this name is correct.\n"
            reply += "2. No, I need to re-type the name."
            return[reply]
        
        # Moderator indicates if they would like to confirm the review
        elif self.state == State.CONFIRMING_REVIEW:
            if message.content == "1":
                if self.abuse_type == "Doxxing" and self.victim_name:
                    # Include perpetrator information when logging victim
                    perpetrator_id = str(self.original_reported_message.author.id) if self.original_reported_message and self.original_reported_message.author else None
                    perpetrator_name = self.original_reported_message.author.display_name if self.original_reported_message and self.original_reported_message.author else None
                    if self.victim_name != "Unknown":
                        insert_victim_log(self.victim_name, self.timestamp, perpetrator_id, perpetrator_name)
                await message.author.send("Finalizing your review...")
                await self._submit_report_to_mods()
                self.state = State.REVIEW_COMPLETE
                return ["Review finalized. Outcome logged to the moderator channel. Type the password to start a new review."]
            elif message.content == "2":
                self.state = State.REVIEW_COMPLETE
                return ["Review cancelled. Type the password to begin again."]
            else:
                return ["Invalid input. Please type 1 to Confirm or 2 to Cancel."]
        
        return ["An error occurred. Please type `cancel` or contact an admin."]
    
    async def _execute_moderation_actions(self):
        """
        Performs automated moderation actions (message deletion, user suspension) 
        based on the flags set during the review process

        """
        actions_taken_summary_list = []

        # Prepare update messages for reporter and (potential) offender
        original_content = f"```{self.original_reported_message.content[:1000]}```" + ("... (truncated)" if len(self.original_reported_message.content) > 1000 else "")
        action_for_reporter = f"Your report of the following post has been reviewed:\nReason for report: {self.abuse_type.lower()}\n"
        action_for_offender = ""
        
        if not self.original_reported_message or not self.original_reported_message.author:
            actions_taken_summary_list.append("Critical Error: Original message/author not identified by bot.")
            return actions_taken_summary_list

        # Attempt to delete reported message if appropriate
        if self.remove:
            try:
                await self.original_reported_message.delete()
                actions_taken_summary_list.append("Original message **deleted**.")
                action_for_reporter += "The message is now deleted."
                action_for_offender += f"The following message of yours was reported as {self.abuse_type.lower()}:\n{original_content}\nAs a result of this report, your message was deleted."
                insert_perpetrator_log(str(self.original_reported_message.author.id), self.original_reported_message.author.display_name, datetime.now(), self.victim_name, self.risk_level)
                await self._send_appropriate_warning()
            except discord.Forbidden:
                actions_taken_summary_list.append("Bot **failed to delete** message (Permissions error).")
                action_for_reporter += "Unfortunately, the message could not be deleted due to server errors. We will work to fix this."
            except discord.NotFound:
                actions_taken_summary_list.append("Original message **not found** (already deleted?).")
                action_for_reporter += "The message is now deleted."
            except discord.HTTPException as e:
                actions_taken_summary_list.append(f"Bot **failed to delete** message (HTTP Error: {e.status}).")
                action_for_reporter += "Unfortunately, the message could not be deleted due to server errors. We will work to fix this."

        # Attempt to suspend user if appropriate
        # if self.suspend_user:
        #     if isinstance(self.original_reported_message.author, discord.Member):
        #         try:
        #             timeout_duration = timedelta(days=1)
        #             actions_taken_summary_list.append(f"User `{self.original_reported_message.author.mention}` **would be suspended for 1 day** (TESTING - action disabled).")
        #             action_for_reporter += " Action has been taken against the user."
        #             action_for_offender += " Your account has also been suspended for 1 day."
        #         except discord.Forbidden:
        #             actions_taken_summary_list.append(f"Bot **failed to suspend** user `{self.original_reported_message.author}` (Permissions error).")
        #         except discord.HTTPException as e:
        #             actions_taken_summary_list.append(f"Bot **failed to suspend** user `{self.original_reported_message.author}` (HTTP Error: {e.status}).")
        #     else:
        #         actions_taken_summary_list.append(f"User `{self.original_reported_message.author}` **could not be suspended** (not a current server member).")

        # Report was rejected, send update only to reporter
        if not actions_taken_summary_list: 
            action_for_reporter += f"\n{original_content}\nThe moderation team does not believe your post falls under the category listed. No action was taken."
            actions_taken_summary_list.append("No automated actions (delete/suspend) triggered (e.g., no direct threat ID'd by reviewer).")

        # Abuse detected. Send updates to reporter (if non-bot) and offender.
        if self.reporter:
            await self.reporter.send(action_for_reporter + " Thank you for your report.")
        if action_for_offender:
            await self.original_reported_message.author.send(action_for_offender + " Future offenses may result in further action taken against your account. We recommend reviewing our platform policies to ensure you avoid future violations.")

        return actions_taken_summary_list

    async def _send_appropriate_warning(self):
        author = self.original_reported_message.author
        perp_score = get_perpetrator_score(str(author.id))
        print(perp_score)
        if perp_score < 3 and author.id in self.warned:
            self.warned.remove(author.id)
        # Check for consequences based on harassment count
        if perp_score >= 3 and (perp_score < 5 or author.id not in self.warned):
            # Send warning card to channel
            warning_embed = discord.Embed(
                title="**Official Warning**",
                color=0xf1c40f,  # Yellow
                timestamp=datetime.now()
            )
            warning_embed.add_field(name="**User**", value=f"{author.mention} (`{author.display_name}`, ID: `{author.id}`)", inline=False)
            warning_embed.add_field(name="**Action**", value="**Warning Issued**", inline=True)
            warning_embed.add_field(name="**Reason**", value="Multiple or severe doxxing violations detected by automated system", inline=True)
            warning_embed.add_field(name="**Notice**", value="Continued violations may result in suspension. Please review community guidelines.", inline=False)
            warning_embed.set_footer(text="Automated Moderation System")
            
            await author.send(embed=warning_embed)
            await self.mod_channel.send(f"User {author.mention} was sent a warning.")
            self.warned.add(author.id)
            
        elif perp_score >= 5 and perp_score < 10:
            # Send suspension notification card to channel
            suspension_embed = discord.Embed(
                title="**Suspension Notice**",
                color=0xe74c3c,  # Red
                timestamp=datetime.now()
            )
            suspension_embed.add_field(name="**User**", value=f"{author.mention} (`{author.display_name}`, ID: `{author.id}`)", inline=False)
            suspension_embed.add_field(name="**Action**", value="**Suspension Issued**", inline=True)
            suspension_embed.add_field(name="**Reason**", value="Persistent doxxing violations detected by automated system", inline=True)
            suspension_embed.add_field(name="**Note**", value="**This is a demonstration.** In a live environment, this account would have user privileges restricted for three (3) days. Future offenses may result in further account action.", inline=False)
            suspension_embed.set_footer(text="Automated Moderation System")
            
            await author.send(embed=suspension_embed)
            await self.mod_channel.send(f"User {author.mention} was suspended for three (3) days.")
            self.warned.add(author.id)
        
        elif perp_score > 10:
            # Send suspension notification card to channel
            suspension_embed = discord.Embed(
                title="**Account Banned Notice**",
                color=0xe74c3c,  # Red
                timestamp=datetime.now()
            )
            suspension_embed.add_field(name="**User**", value=f"{author.mention} (`{author.display_name}`, ID: `{author.id}`)", inline=False)
            suspension_embed.add_field(name="**Action**", value="**Ban Issued**", inline=True)
            suspension_embed.add_field(name="**Reason**", value="Persistent doxxing violations detected by automated system after suspension", inline=True)
            suspension_embed.add_field(name="**Note**", value="**This is a demonstration.** In a live environment, this account would be banned from the platform.", inline=False)
            suspension_embed.set_footer(text="Automated Moderation System")
            
            await author.send(embed=suspension_embed)
            await self.mod_channel.send(f"User {author.mention} was banned from the platform.")
            self.warned.add(author.id)

    async def _submit_report_to_mods(self):
        """
        Send the review to the moderator channel for the guild.
        """
        if not self.report:
            return
        
        reviewer_name = "Moderator (Reviewer ID N/A)" 
        actions_performed_strings = await self._execute_moderation_actions()
        summary_lines = []
        summary_lines.append(f"**Review of Report: `{self.report.title}`**") 
        if self.original_reported_message and self.original_reported_message.author:
            summary_lines.append(f"Original Msg Author: `{self.original_reported_message.author}`)")
            summary_lines.append(f"Original Msg Link: [Click to View]({self.original_reported_message.jump_url})")
        else:
            summary_lines.append("Warning: Original msg/author details unavailable.")

        # Reviewer's assessment
        summary_lines.append("\n**Moderator's Assessment:**")
        summary_lines.append(f"- Threat of Violence: `{'Yes' if self.threat_identified_by_reviewer else 'No'}`")
        if self.abuse_type == "Doxxing":
            summary_lines.append(f"- Disallowed Info: `{'Yes' if self.disallowed_info_identified else 'No'}`")
        summary_lines.append(f"- Other Problematic Content: `{'Yes' if self.other_pii_identified else 'No'}`")

        summary_lines.append("\n**Outcome:**")
        summary_lines.append("- Status: First-Level Review Completed.")
        summary_lines.append("\n  **Automated Bot Actions:**")
        if actions_performed_strings:
            for item in actions_performed_strings: summary_lines.append(f"    - {item}")
        else: 
            summary_lines.append("    - No automated actions logged.") 
        
        if (not self.threat_identified_by_reviewer and 
            (self.disallowed_info_identified or self.other_pii_identified)):
                 summary_lines.append("\n  Note: Other violations noted. Manual follow-up may be needed.")

        final_summary_text = "\n".join(summary_lines)
        
        embed_title = "Review Finalized"
        embed_color = discord.Color.dark_grey()
        if self.threat_identified_by_reviewer: 
            embed_title, embed_color = "Review: Actions Taken/Logged", discord.Color.green()
        elif (self.disallowed_info_identified or self.other_pii_identified): 
            embed_title, embed_color = "Review: Findings Logged", discord.Color.blue()

        self.mod_channel = self.client.mod_channels.get(self.guild_id)
        if not mod_channel:
            return

        review_embed = discord.Embed(title=embed_title, description=final_summary_text, color=embed_color, timestamp=datetime.now())
        review_embed.set_footer(text=f"Review by: {reviewer_name} | Bot v2.2")
        try:
            await self.mod_channel.send(embed=review_embed)
            if self.reports.empty():
                await self.mod_channel.send(f"There are no more reports to review. Amazing work, everyone!")
            elif self.reports.qsize() == 1:
                await self.mod_channel.send(f"There is now {self.reports.qsize()} report left to review.")
            else:
                await self.mod_channel.send(f"There are now {self.reports.qsize()} reports left to review.")
        except discord.Forbidden:
            pass
        except discord.HTTPException as e:
            pass

    def get_help_message(self):
        help_msg = "**Discord Review Bot Help**\n\n"
        help_msg += "At any time, you may do the following:\n"
        help_msg += f"- Type `{self.HELP_KEYWORD}` to see a help message.\n"
        help_msg += f"- Type `{self.CANCEL_KEYWORD}` to log out of the review bot. This will cancel any in-progress reviews.\n"
        help_msg += f"- Type `{self.DETAILS_KEYWORD} [Evaluation ID]` to review a bot's doxxing evaluation.\n"
        help_msg += f"- Type `{self.POLICY_KEYWORD}` to read our doxxing policy.\n"
        
        if self.state == State.AWAITING_CONTINUE:
            help_msg += f"You have not begun a review yet. To begin a review, type `{self.REVIEW_KEYWORD}`\n\n"

        elif self.state == State.AWAITING_THREAT_JUDGEMENT:
            help_msg += "Please identify whether the post in question contains a threat of violence. Posts labeled as a threat will be removed.\n"
            help_msg += "1. Yes, a threat is present.\n"
            help_msg += "2. No, a threat is **not** present."

        elif self.state == State.AWAITING_OTHER_ABUSE_JUDGEMENT:
            help_msg += f"The reason for report was: **{self.abuse_type.lower()}**.\nDoes the post in question meet that criteria?\n"
            help_msg += f"1. Yes, the post contains {self.abuse_type.lower()}.\n"
            help_msg += f"2. No, the post does **not** contain {self.abuse_type.lower()}."
        
        elif self.state == State.AWAITING_DISALLOWED_INFO:
            help_msg += "The following information is never allowed on our platform:\n"
            help_msg += " - Government ID (e.g. Social Security Numbers, ID numbers, etc.)\n"
            help_msg += " - Personal financial information (e.g. bank account numbers, credit card numbers, etc.\n"
            help_msg += "It is important to know if this post contains any of that information. Posts labeled as containing disallowed information will be removed and the users will be suspended. Does this post contain disallowed information?\n"
            help_msg += "1. Yes, this post **contains expressly disallowed information**\n"
            help_msg += "2. No, it does not.\n"
        
        elif self.state == State.AWAITING_CONTENT_CHECK:
            help_msg += "Please type `1` if the post contains other personally identifiable information, such as phone, email, location, employer. Type `2` otherwise."
        
        elif self.state == State.AWAITING_INTENTION:
            help_msg += "Any individual or business may post their own information (except for government and financial information). Otherwise, we have stricter policy guidelines.\n"
            help_msg += "Private and potentially sensitive information posted about a **business** must **lack bad faith**. Neutral posts are allowed."
            help_msg += "Private and potentially sensitive information posted about an **individual** must be shared in **good faith**. This is a higher threshold than for businesses - ambiguous posts should be removed.\n"
            help_msg += "Enter `1` if:\n"
            help_msg += " - A person is posting their own information.\n"
            help_msg += " - A businesses information is posted and there is no bad intent.\n"
            help_msg += " - An individual's information is posted and there is **good** intent.\n"
            help_msg += "Otherwise, enter `2`."

        elif self.state == State.AWAITING_NAME:
            help_msg += "Please type the name of the individual who is being doxxed."
        
        elif self.state == State.NAME_CONFIRMATION:
            help_msg += f"It is important that we have the correct victim name in our database. The victim name on file for this report is `{self.victim_name}`. Type `1` if this is the correct name and `2` if this name is incorrect."

        return help_msg
    
    def review_complete(self):
        return self.state == State.REVIEW_COMPLETE
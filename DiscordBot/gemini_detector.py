# gemini_detector.py
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel
import discord
from datetime import datetime
from supabase_helper import victim_score

class GeminiDoxxingDetector:
    def __init__(self, project_id: str, location: str = "us-central1"):
        # Set up Google Cloud credentials
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'
        
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)
        
        # Load Gemini model
        # Try these models in order of preference
        self.model = GenerativeModel("gemini-2.0-flash-001")
        
        print(f"✅ Gemini detector initialized for project: {project_id}")
    
    def analyze_for_doxxing(self, message_content: str, author_name: str = "Unknown"):
        """
        Analyze a Discord message for doxxing using Gemini AI
        """
        
        prompt = f"""You are an elite content moderator with 10+ years of experience detecting doxxing, harassment, and privacy violations across social platforms. You understand the nuanced difference between legitimate information sharing and malicious doxxing.

ANALYZE THIS DISCORD MESSAGE FOR DOXXING:

AUTHOR: {author_name}
MESSAGE: "{message_content}"

=== DOXXING DETECTION FRAMEWORK ===

HIGH-RISK DOXXING INDICATORS:
• Personal identifiers + location data (full name + address/city + state)
• Contact information shared without consent (phone, personal email, home address)
• Government/financial IDs (SSN, license plates, bank accounts, credit cards)
• Private family information (children's schools, spouse workplace, home photos)
• Workplace harassment setup (job title + company + personal details)
• Revenge doxxing patterns (ex-partner info, private photos, social accounts)
• Threats to release or search for any of the above information (including in exchange for favors or money)

MEDIUM-RISK PRIVACY CONCERNS:
• Partial personal information that could enable targeting
• Professional info shared with malicious context
• Location data that narrows down private residence
• Social media accounts of private individuals
• Information that enables further stalking/harassment

CONTEXTUAL ANALYSIS PRIORITIES:
1. CONSENT: Did the person consent to this information being shared? Is there any indication that this information is being revealed rather than already being public?
2. INTENT: Is this meant to help or harm the target?
3. SPECIFICITY: How precise is the identifying information?
4. VULNERABILITY: Is the target in a vulnerable position?
5. ESCALATION: Does this fit a pattern of increasing harassment?
6. TONE: Does the message use obvious sarcasm, absurdity, or exaggeration that undermines doxxing risk? Be cautious not to flag jokes unless they contain real identifiers.


ADVANCED PATTERN RECOGNITION:
• Look for coded language or euphemisms for doxxing
• Detect "breadcrumb" doxxing (small details that accumulate)
• Identify coordinated harassment indicators
• Recognize victim-blaming or justification narratives
• Spot "just asking questions" that seek personal info
• Be alert to messy or informal language (abbreviations, emojis, slang, voice-to-text errors)


CONFIDENCE CALIBRATION:
• 0.95-1.0: Crystal clear doxxing or obviously innocent content
• 0.85-0.94: Strong evidence with minor ambiguity
• 0.70-0.84: Clear indicators but some context missing
• 0.50-0.69: Concerning elements but significant uncertainty
• 0.30-0.49: Possible issues but likely innocent
• 0.10-0.29: Minimal concern, probably safe
• 0.00-0.09: Definitely not doxxing

SPECIAL CONSIDERATIONS & EDGE CASES:
• Self-disclosure: People sharing their OWN info (usually OK unless coerced)
• Public figures and events: Already public info may be less concerning
• Business context: Official business information vs personal details
• Gaming/online personas: Distinguish usernames from real identity
• Historical/fictional: Past events or fictional characters
• News/reporting: Legitimate information sharing vs harassment

=== DETAILED EDGE CASE EXAMPLES ===

TRICKY SELF-DISCLOSURE SCENARIOS:
• "I'm Sarah Johnson, meet me at Starbucks on 5th Street" (OK - own info, public place)
• "My address is 123 Oak Lane if anyone wants to send hate mail" (CONCERNING - self-doxxing under duress/emotional distress)
• "I work at Google as a software engineer, AMA" (OK - general professional info)
• "I'm the night janitor at Lincoln Elementary, I have keys to everywhere" (CONCERNING - security implications)

AMBIGUOUS THIRD-PARTY INFORMATION:
• "My friend Jake lives in Seattle" (LOW RISK - very general)
• "Jake Thompson from Roosevelt High is spreading rumors" (MEDIUM - specific school + full name)
• "That's definitely Mike from accounting, he drives the red Tesla" (LOW-MEDIUM - workplace + identifying detail but vague)
• "Mike Johnson, the guy who works at First National Bank downtown" (HIGH - specific workplace + full name)

CODED/INDIRECT DOXXING:
• "Someone should visit the teacher who gave me an F, she lives on Maple Street" (HIGH - implied threat + location)
• "Wouldn't it be crazy if someone called this number: 555-0123" (HIGH - phone number with implied harassment)
• "I found his mom's Facebook, should I message her?" (MEDIUM-HIGH - family harassment setup)
• "DM me for more details about this person" (MEDIUM - soliciting private info sharing)

THREAT OF DOXXING:
• "I will tell everyone where you live unless you hire me" (MEDIUM - implied harassment and threat of doxxing location)
• "If you pay me, I'll find out where he works for you" (MEDIUM - implied harassment and threat of doxxing employer information)
• "For an extra fee, you can get this delivered straight to your house" (OK - business advertising services)

PUBLIC VS PRIVATE FIGURE CONFUSION:
• "Local news anchor Sarah Smith lives at..." (MEDIUM-HIGH - local public figure but home address)
• "YouTuber PewDiePie's real address is..." (HIGH - even famous people deserve privacy)
• "Teacher Mrs. Johnson from our school posts on Instagram @..." (MEDIUM - semi-public role, private social media)
• "The mayor's daughter goes to Lincoln High" (LOW-MEDIUM - public figure's family, general info)

BUSINESS INFORMATION GRAY AREAS:
• "Call Johnson's Plumbing at 555-PIPE for great service!" (OK - business promotion)
• "Don't hire Johnson's Plumbing, the owner John lives at 123 Oak" (HIGH - business dispute + home address)
• "I work at McDonald's on 5th Street, the manager is horrible" (LOW - general workplace complaint)
• "The manager Sarah at McDonald's on 5th gave me her personal number" (MEDIUM - specific person + potential harassment setup)

GAMING/ONLINE IDENTITY CROSSOVER:
• "GamerTag123 is actually named Mike" (LOW - just connecting username to first name)
• "GamerTag123 goes to Roosevelt High and his real name is Mike Johnson" (HIGH - specific school + full name)
• "Streamer_Girl is cute, I found her Instagram" (MEDIUM-HIGH - connecting platforms for potentially romantic harassment)
• "That Twitch streamer lives in my city, I see her at Starbucks sometimes" (MEDIUM - real-world stalking implications)

FAMILY/RELATIONSHIP INFORMATION:
• "My girlfriend Sarah is being crazy" (OK - own relationship discussion)
• "This crazy girl Sarah Thompson keeps texting me" (MEDIUM - full name in complaint context)
• "Sarah's kids go to Lincoln Elementary, she picks them up at 3pm" (HIGH - children's routine + location)
• "My ex-wife works at the bank downtown" (LOW-MEDIUM - general location, relationship context matters)

SCREENSHOTS AND INDIRECT SHARING:
• "Look at this public Facebook post [screenshot]" (LOW - already public content)
• "Check out this private conversation [screenshot with phone numbers visible]" (HIGH - private content + contact info)
• "This person's profile says they live in..." (MEDIUM - depends on context and specificity)
• "Found this person's dating profile, look how desperate" (MEDIUM-HIGH - harassment + potentially private platform)

CONTEXTUAL INTENT MATTERS:
• "John Smith from accounting got promoted, congrats!" (OK - positive workplace news)
• "John Smith from accounting is stealing, someone should report him to 555-0123" (HIGH - accusation + phone number)
• "If you see Mike Johnson around town, tell him he owes me money" (MEDIUM - public call-out, potential harassment)
• "Mike Johnson helped me with my car, great guy!" (OK - positive reference)
• "Isn't your real name Courtney Bryson?" (MEDIUM - depends on context, implied sharing of secret information)

PARTIAL INFORMATION ACCUMULATION:
• Message 1: "This guy in my math class is annoying"
• Message 2: "He drives a blue Honda"  
• Message 3: "His name starts with J"
• Message 4: "He works at the pizza place on Main Street"
(CONCERNING PATTERN - breadcrumb doxxing building identifying profile)

=== RESPONSE REQUIREMENTS ===

For "who_was_doxxed": Be specific. If it is known, include the person's full name. If you do not know who was doxxed, say "Unknown".
For "sensitive_details": List exact items found - "home address: 123 Oak St, phone: 555-0123"
For "reasoning": Give a concise analysis - 1-2 sentence explaination of your decision-making process.
For "primary_concern": Make it actionable - what exact harm could result?
For "immediate_risks": Be concrete - "target could be visited at home", "harassment campaign"
For "follow_up_needed": Suggest specific next steps - "monitor author for escalation", "check for coordinated attack"

CRITICAL: Vary confidence scores naturally based on actual certainty. Don't default to middle values.

WRITING STYLE: Use normal sentence capitalization. Do NOT capitalize every word. Write naturally like a human moderator would."

Respond with ONLY valid JSON:
{{
    "is_doxxing": true/false,
    "confidence": 0.85,
    "risk_level": "HIGH/MEDIUM/LOW/MINIMAL",
    "target_analysis": {{
        "who_was_doxxed": "Full name of the person who was doxxed. If you do not know, say 'Unknown'",
        "relationship_to_author": "self/friend/stranger/enemy/unknown - include any context about their relationship",
        "is_public_figure": true/false,
        "apparent_consent": "explicit/implied/none/unknown - explain what indicates consent level"
    }},
    "information_disclosed": {{
        "info_types_found": ["real_name", "address", "phone", "email", "workplace", "family_info", "financial", "government_id", "social_media", "photos"],
        "specificity_level": "exact/approximate/vague - describe how precise the information is",
        "sensitive_details": ["List every specific sensitive item found with exact details where possible"],
        "partial_info": "Detailed description of incomplete but concerning information that could enable further doxxing"
    }},
    "context_analysis": {{
        "apparent_intent": "malicious/helpful/neutral/unclear - explain what suggests this intent",
        "conversation_tone": "aggressive/casual/concerned/playful - describe the emotional context",
        "potential_harm_level": "immediate/future/minimal/none - specify what harm could result",
        "escalation_indicators": ["List specific signs this could escalate: threats, harassment_history, coordinated_attack, revenge_context, vulnerability_exploitation, none"]
    }},
    "moderator_summary": {{
        "primary_concern": "Detailed one-line summary explaining the main risk and why it matters",
        "immediate_risks": ["Comprehensive list of specific immediate dangers to the target"],
        "reasoning": "Thorough step-by-step analysis: What information was shared? Why is it concerning? What context clues inform your decision? What harm could result? Why this confidence level?",
        "recommended_action": "remove_immediately/warn_user/monitor_closely/no_action_needed - with brief justification",
        "follow_up_needed": "Specific actionable steps: monitor patterns, check for coordination, verify target identity, escalate to authorities, etc."
    }}
}}"""
        try:
            # Call Gemini
            response = self.model.generate_content(prompt)
            
            # Clean up response
            result_text = response.text.strip()
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].strip()
            
            # Parse JSON
            analysis = json.loads(result_text)
            
            # Ensure confidence is between 0 and 1
            if 'confidence' in analysis:
                analysis['confidence'] = max(0.0, min(1.0, float(analysis['confidence'])))
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error calling Gemini: {e}")
            return {
                "is_doxxing": False,
                "confidence": 0.0,
                "reasoning": f"Analysis failed: {str(e)}"
            }

class ProcessingGeminiResponse:
    def __init__(self, analysis, message):
        self.analysis = analysis
        self.message = message

    def format_bot_response(self):
        """
        Format the detailed doxxing analysis for display. Three return variables:
            embed - the embed that should be sent to the moderator channel with a summary of response (None if no doxxing)
            bot_report - string with details of bot's decision making process (None if no doxxing)
            risk - bot's assessment of risk, represented as an integer (None if no doxxing or >84% confidence of doxxing)
            confidence - bot's confidence in doxxing assessment (None if no doxxing)
        """
        
        if not self.analysis.get('is_doxxing', False):
            return None, None, None, None, None
        
        # Extract key information
        confidence = float(self.analysis.get('confidence', 0))
        risk_level = self.analysis.get('risk_level', 'UNKNOWN')
        
        # Target information
        target_info = self.analysis.get('target_analysis', {})
        who_doxxed = target_info.get('who_was_doxxed', 'Unknown person')
        relationship = target_info.get('relationship_to_author', 'unknown')
        
        # What information was shared
        info_disclosed = self.analysis.get('information_disclosed', {})
        info_types = info_disclosed.get('info_types_found', [])
        sensitive_details = info_disclosed.get('sensitive_details', [])
        
        # Context and intent
        context = self.analysis.get('context_analysis', {})
        intent = context.get('apparent_intent', 'unclear')
        harm_level = context.get('potential_harm_level', 'unknown')
        
        # Moderator summary
        mod_summary = self.analysis.get('moderator_summary', {})
        primary_concern = mod_summary.get('primary_concern', 'Privacy violation detected')
        reasoning = mod_summary.get('reasoning', 'No detailed reasoning provided')
        action = mod_summary.get('recommended_action', 'review_needed')

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
        
        # Format the report
        bot_report = f"""
    **🚨 DOXXING DETECTED - {risk_level} RISK**

    **👤 Target:** {who_doxxed} ({relationship} to author)
    **📊 Confidence:** {confidence * 100}%
    **⚠️ Primary Concern:** {primary_concern}

    **📋 Information Exposed:**
    • Types: {info_text}
    • Sensitive Details: {', '.join(sensitive_details) if sensitive_details else 'See message content'}

    **🎯 Context Analysis:**
    • Intent: {intent.title()}
    • Harm Level: {harm_level.title()}

    **🤖 AI Analysis:** {reasoning}

    **✅ Recommended Action:** {action.replace('_', ' ').title()}
        """

        # High confidence: post will be automatically deleted
        if confidence > 0.84:
            embed = discord.Embed(
                title=f"Post Automatically Removed for Doxxing: {risk_level} Risk",
                timestamp=datetime.now() # Timestamp of when the report was initiated
            )
        
            embed.add_field(name="**Victim Name**", value=f"```{who_doxxed}```", inline=False)
            embed.add_field(name="**Author of Reported Message**", value=f"{self.message.author.mention} (`{self.message.author.name}`, ID: `{self.message.author.id}`)", inline=True)

            # If Doxxing info types were collected, add them to the embed
            embed.add_field(name="**Doxxing Information Types Reported**", value={', '.join(info_types) if info_types else 'Various personal details'}, inline=False)
                
            embed.add_field(name="**Harm Assessment**", value={harm_level.title()}, inline=False)

            embed.add_field(name="**Result**", value="✅ **Automatic Action Taken:** Message deleted and user notified.", inline=False)
                        
            return embed, bot_report.strip(), None, confidence, None
        
        # Medium confidence: post will be sent for manual review
        if confidence > 0.5:
            doxxing_score = 0
            if who_doxxed != "Unknown":
                doxxing_score = victim_score(who_doxxed)

            embed_color, risk_number = self._get_risk_values(risk_level, doxxing_score)

            embed = discord.Embed(
                title=f"Added by Bot to Review Queue: {risk_level} Doxxing Risk, medium confidence",
                color=embed_color,
                timestamp=datetime.now() # Timestamp of when the report was initiated
            )

            embed.add_field(name="**Content of Reported Message**", value=f"```{self.message.content[:1000]}```" + ("... (truncated)" if len(self.message.content) > 1000 else ""), inline=False)
            embed.add_field(name="**Author of Reported Message**", value=f"{self.message.author.mention} (`{self.message.author.name}`, ID: `{self.message.author.id}`)", inline=True)
            embed.add_field(name="**Filed By (Reporter)**", value=f"MODERATOR BOT", inline=True)

            embed.add_field(name="**Specific Reason Provided by Reporter**", value="Doxxing", inline=False)
            
            embed.add_field(name="**Victim Name**", value=who_doxxed, inline=False)

            embed.add_field(name="**Doxxing Information Types Reported**", value={', '.join(info_types) if info_types else 'Various personal details'}, inline=False)
                
            embed.add_field(name="**Harm Assessment**", value=harm_level.title(), inline=False)
                
            embed.add_field(name="**Direct Link to Reported Message**", value=f"[Click to View Message]({self.message.jump_url})", inline=False)

            return embed, bot_report.strip(), risk_number, confidence, doxxing_score
        
        return None, None, None, confidence, None
    
    def _get_risk_values(self, risk, doxxing_score):
        """
        Return a color based on the AI bot's risk level and doxxing score.
        Return number based on AI bot's risk level.
        """
        color = 0x95a5a6
        number = 1
        if risk == "Minimal" or (doxxing_score > 0 and doxxing_score < 10):
            color = 0x3498db   # Blue
        elif risk == "Low" or doxxing_score < 30:
            color = 0xf1c40f   # Yellow
        elif risk == "Medium" or doxxing_score < 50:
            color = 0xe67e22   # Orange
        elif risk == "High" or doxxing_score > 0:
            color = 0xe74c3c   # Red
        if risk == "Minimal":
            number = 1
        elif risk == "Low":
            number = 2
        elif risk == "Medium":
            number = 3
        elif risk == "High":
            number = 4
        return color, number  # Grey (default/unknown)
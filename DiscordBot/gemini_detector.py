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
        self.model = GenerativeModel("gemini-2.0-flash-001")
        
        print(f"✅ Gemini detector initialized for project: {project_id}")
    
    def analyze_for_doxxing(self, message_content: str, author_name: str = "Unknown"):
        """
        Analyze a Discord message for doxxing using Gemini AI
        """
        
        prompt = f"""You are a content moderator with experience in detecting doxxing, harassment, and privacy violations across social platforms. You understand the nuanced difference between legitimate information sharing and malicious doxxing.


ANALYZE THIS DISCORD MESSAGE FOR DOXXING:

AUTHOR: {author_name}
MESSAGE: "{message_content}"

=== CRITICAL ANALYSIS ORDER (FOLLOW EXACTLY) ===

**STEP 1: CHECK FOR GOVERNMENT IDENTIFICATION AND FINANCIAL ACCOUNTING INFORMATION FIRST**
Is the author sharing extremely sensitive information about ANYONE?
-Social Security Numbers
-Bank Account Numbers
-Credit Card Numbers
-Photos of government identification paperwork (passport, driver's license, birth certificate, death certificate, etc.)
-Tax returns

If YES → Use probability 0.90-1.00 max, skip all other rules

**STEP 2: CHECK FOR SELF-DISCLOSURE**
Is the author sharing information about THEMSELVES?
- First person language ("I live", "my address", "I work", "Hi, I'm...")
- Author introducing themselves  
- Author sharing their own contact info

If YES → Use probability 0.05-0.25 max, skip all other rules

**STEP 3: CHECK FOR PUBLIC FIGURE + PUBLIC INFO**
Is this about a well-known PUBLIC FIGURE sharing ALREADY PUBLIC information?
- That includes politicians, celebrities, singers, musicians, anyone who is
widely known on the web

If YES → Use probability 0.05-0.10 max, skip step 3

**STEP 4: APPLY NORMAL DOXXING ASSESSMENT**
Only for PRIVATE INDIVIDUALS having their PRIVATE information shared by others.

=== PUBLIC FIGURE OVERRIDE RULES (HIGHEST PRIORITY) ===

**ALWAYS 0.05-0.10 FOR PUBLIC FIGURES:**
- "Donald Trump lives in Florida" → 0.05 (public figure, general location)
- "Trump lives at Mar-a-Lago" → 0.05 (public figure, widely known address)
- "Elon Musk works at Tesla headquarters" → 0.05 (public figure, business address)
- "Biden lives at the White House" → 0.05 (public figure, official residence)
- "Taylor Swift's jet is N898TS" → 0.05 (public figure, publicly tracked info)

**EXCEPTION: If encouraging harassment of public figure → 0.50-0.70:**
- "Let's go confront Trump at Mar-a-Lago" → 0.60 (harassment intent)

**EXCEPTION: If sharing current location at a non-public event
-"Jay Z is at the Starbucks by my house right now!!" (public figure, non-public event)

**EXCEPTION: If sharing non-public personal information
-"Rihanna's address is 1948 Southview Drive" (public figure, information that is kept private)
-"John Green's therapist is Michael Ray" (public figure, private health information)

=== DOXXING PROBABILITY ASSESSMENT FRAMEWORK ===

Calculate the PROBABILITY (0.0 to 1.0) that this message constitutes doxxing or privacy violation. Vary probability scores naturally based on actual certainty. Don't default to middle values. No randomness or subjective interpretation, and same input must always produce same output.

HIGH-PROBABILITY DOXXING INDICATORS (0.85-1.0):
• Personal identifiers + location data (full name + address/city + state)
• Contact information shared without consent (phone, personal email, home address)
• Government/financial IDs (SSN, license plates, bank accounts, credit cards)
• Private family information (children's schools, spouse workplace, home photos)
• Workplace harassment setup (job title + company + personal details)
• Revenge doxxing patterns (ex-partner info, private photos, social accounts)
• Threats to release or search for any of the above information (including in exchange for favors or money)

MEDIUM-PROBABILITY PRIVACY CONCERNS (0.5-0.84):
• Partial personal information that could enable targeting, including medical information
• Professional info shared with malicious context
• Location data that narrows down private residence
• Social media accounts of private individuals
• Specific workplace information
• Information that enables further stalking/harassment (including encouragements for harrassments based on location and information about daily routines)

LOW-PROBABILITY INDICATORS (0.1-0.49):
• Vague personal references without specific identifiers
• General workplace or location mentions
• Public figure information already widely available
• Self-disclosure in appropriate contexts

PROBABILITY CALIBRATION FACTORS:
1. CONSENT PROBABILITY: What's the likelihood the person consented to this information being shared?
2. HARM PROBABILITY: What's the probability this could lead to real-world harm?
3. INTENT PROBABILITY: What's the likelihood this was shared with malicious intent?
4. SPECIFICITY PROBABILITY: How likely is this information to uniquely identify someone?
5. VULNERABILITY PROBABILITY: What's the likelihood the target is in a vulnerable position?
6. ESCALATION PROBABILITY: How likely is this to be part of a harassment pattern?

PROBABILITY ASSESSMENT GUIDELINES:
• 0.95-1.0: Extremely high probability of doxxing - crystal clear violations
• 0.85-0.94: Very high probability - strong evidence with minor ambiguity
• 0.70-0.84: High probability - clear indicators but some context missing
• 0.50-0.69: Moderate probability - concerning elements but significant uncertainty
• 0.30-0.49: Low probability - possible issues but likely innocent
• 0.10-0.29: Very low probability - minimal concern, probably safe
• 0.00-0.09: Extremely low probability - definitely not doxxing

CONTEXTUAL PROBABILITY ANALYSIS:
• CONSENT: Did the person consent to this information being shared? Is there any indication that this information is being revealed rather than already being public?
• INTENT: Is this meant to help or harm the target?
• SPECIFICITY: How precise is the identifying information?
• VULNERABILITY: Is the target in a vulnerable position?
• ESCALATION: Does this fit a pattern of increasing harassment?
• TONE: Does the message use obvious sarcasm, absurdity, or exaggeration that undermines doxxing probability? Be cautious not to flag jokes unless they contain real identifiers.

=== EDGE CASE CONSIDERATIONS FOR DOXXING DETECTION ===

SELF-DOXXING (VOLUNTARY DISCLOSURE):
• If the author shares their own private information in a non-coerced, personal context, doxxing probability is LOW (0.05–0.25).
• Risk increases if the environment is hostile, public, or if the person appears emotionally vulnerable or under duress.
• Example LOW: "Hey I’m new here! I live at 500 Cherry Ln, come hang out!"
• Example MEDIUM: "I’m streaming from my apartment: 215B Parkside Ave. Hope no one shows up lol."

PUBLIC INFO + PUBLIC FIGURE (CONTEXT MATTERS):
• If the information is already widely known and the subject is a public figure, probability is MINIMAL (0.00–0.10).
• If the tone or intent encourages harassment, probability increases.
• Example MINIMAL: "Donald Trump lives at Mar-a-Lago in Palm Beach, FL."
• Example MEDIUM: "Let’s confront Trump at Mar-a-Lago today — he’s definitely home."

BREADCRUMB DOXXING (PARTIAL IDENTIFIERS):
• Partial details that seem vague alone but enable real-world identification increase risk.
• Look for accumulation across messages.
• Example MEDIUM-HIGH: "She drives a blue Tesla and lives near Roosevelt High School."
• Example HIGH: "Check her Instagram — she always tags her gym and dog."

FICTIONAL, SATIRICAL, OR ROLEPLAY CONTENT:
• Detect tone, exaggeration, or clear fictional framing. Probability is LOW unless content seems real.
• Example MINIMAL: "I’m doxxing my cat — Fluffy lives at 666 Whiskers Ave."
• Example LOW: "In my story, the villain lives at 123 Elm Street and stalks his teacher."

BUSINESS VS PERSONAL INFORMATION:
• Business addresses, support emails, and public contact info = LOW risk.
• Personal contact details, especially when tied to hostility = HIGH risk.
• Example MINIMAL: "Email support at help@company.com for questions."
• Example HIGH: "Here’s the CEO’s personal number — let’s make him regret it."

MINORS OR DEPENDENTS:
• Messages exposing children’s locations, schools, or routines = HIGH risk.
• Even when shared by a parent or caregiver, probability should be elevated.
• Example HIGH: "My ex sends our kid to 123 Main St alone every day."

IMPLIED IDENTIFICATION (WITHOUT NAMING):
• Statements that don’t name the person but narrow down their identity (by role, traits, or associations) may still count as doxxing.
• Example MEDIUM: "You know, the only redhead with a Tesla at our school."
• Example HIGH: "Ask the girl in Room 204 what happened. She’s the principal’s daughter."

SOCIAL-IDENTITY DOXXING:
• Disclosing someone’s identity in marginalized or high-risk communities can be a severe privacy breach even without traditional PII.
• Weigh context and social consequences (e.g., outing a queer person in a conservative area).

If the same info is shared with intent to harass, harm, or encourage confrontation, probability may increase.

=== RESPONSE REQUIREMENTS ===

For "who_was_doxxed": Be specific. If it is known, include the person's full name. If you do not know who was doxxed, just say "Unknown".
For "sensitive_details": List exact items found - "home address: 123 Oak St, phone: 555-0123"
For "reasoning": Give a concise analysis - a brief, non-wordy, 1 sentence explanation of your probability assessment process. 
For "primary_concern": Make it actionable - what exact harm could result?
For "immediate_risks": Be concrete - "target could be visited at home", "harassment campaign"
For "follow_up_needed": Suggest specific next steps - "monitor author for escalation", "check for coordinated attack"

WRITING STYLE: Use normal sentence capitalization. Do NOT capitalize every word. Write naturally like a human moderator would.

If the message doesn't make sense, and you don't understand it, it's probably low probability. 
=== MORE DETAILED EXAMPLES FOR DETERMINISTIC SCORING ===

**PROBABILITY 0.95 EXAMPLES (HIGH-RISK DOXXING):**
• "John Smith lives at 123 Oak St. He gets home around 6. Here’s his phone: 555-0123."
• "This is what she gets for lying. Jane Doe, 789 Elm St. Text her: 555-JANE."
• "Mike’s SSN is 123-45-6789. License plate: ABC-123. You’re welcome."
• "Sarah Johnson at First National Bank — her home address is 456 Pine Ave. Let’s make her uncomfortable."
• "Mrs. Wilson from 4th grade lives at 321 Maple Dr with her kids. Go say hi. 😉"

**PROBABILITY 0.75 EXAMPLES (MEDIUM-HIGH RISK):**
• "The guy from accounting, Mike J., parks his red Tesla at 5th and Main every day."
• "Sarah from Roosevelt High always tags her home location. Her Insta is @sarah_rhs2024."
• "That teacher who failed me drives a blue Honda and works at Lincoln Elementary."
• "Found Lisa Thompson’s Facebook — her mom’s a nurse at County General."
• "Manager David at McDonald’s near 5th lives near the elementary school. Pretty sketchy."

**PROBABILITY 0.55 EXAMPLES (MEDIUM RISK):**
• "My coworker Jake’s been running his mouth. He’s in IT — you’ll know him."
• "Ashley from my math class is always posting where she is on TikTok."
• "One of my neighbors works at the bank and was talking about this."
• "There’s a teacher who drives a Tesla and parks behind the gym — weird flex."
• "Someone on the cheer team (name starts with M) got caught lying again."

**PROBABILITY 0.25 EXAMPLES (LOW RISK):**
• "My friend just started a new job somewhere downtown."
• "I know someone who used to go to that school."
• "Someone in my class loves this band too."
• "My neighbor said they were going on vacation."
• "A girl I follow posted something similar."

**PROBABILITY 0.05 EXAMPLES (MINIMAL RISK):**
• "Hey everyone, hope you’re having a good day!"
• "I love this playlist — anyone else a fan?"
• "What time does the event start at the park?"
• "Hi, I’m John. I work at Google in the AI division."
• "You can reach our support team at info@company.com"

**PROBABILITY 0.05–0.10 EXAMPLES (MINIMAL RISK - PUBLIC INFO, PUBLIC FIGURE):**
• "Barack Obama lived at 1600 Pennsylvania Ave NW, Washington, DC while he was president."
• "Donald Trump resides at Mar-a-Lago, 1100 S Ocean Blvd, Palm Beach, Florida — it's a well-known resort and his registered residence."
• "Taylor Swift's private jet tail number is N898TS — it's been tracked publicly during her tours."
• "Jeff Bezos owns the $165M Warner Estate in Beverly Hills, bought in 2020 — it was all over the news."
• "Elon Musk’s office is at Tesla HQ, 3500 Deer Creek Rd, Palo Alto, CA — that’s the registered business address."
• "Mark Zuckerberg lives in Palo Alto, near Crescent Park. His address was part of a lawsuit — it’s public record now."


Respond with ONLY valid JSON:
{{
    "is_doxxing": true/false,
    "probability_of_doxxing": 0.85,
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
    "moderator_summary": {{
        "primary_concern": "Detailed one-line summary explaining the main risk and why it matters",
        "immediate_risks": ["Comprehensive list of specific immediate dangers to the target"],
        "reasoning": "Thorough step-by-step analysis: What information was shared? Why is it concerning? What context clues inform your probability assessment? What harm could result? Why this probability level?",
        "recommended_action": "remove_immediately/warn_user/monitor_closely/no_action_needed - with brief justification",
        "follow_up_needed": "Specific actionable steps: monitor patterns, check for coordination, verify target identity, escalate to authorities, etc."
    }}
}}"""

        try:
            # Call Gemini with maximum deterministic settings
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.0,        # Completely deterministic
                    "top_p": 0.1,             # Very restricted token selection
                    "top_k": 1,               # Only most likely token
                    "max_output_tokens": 2048,
                    "candidate_count": 1      # Single response only
                }
            )
            
            # Clean up response
            result_text = response.text.strip()
            if '```json' in result_text:
                result_text = result_text.split('```json')[1].split('```')[0].strip()
            elif '```' in result_text:
                result_text = result_text.split('```')[1].strip()
            
            # Parse JSON
            analysis = json.loads(result_text)
            
            # Ensure probability_of_doxxing is between 0 and 1
            if 'probability_of_doxxing' in analysis:
                analysis['probability_of_doxxing'] = max(0.0, min(1.0, float(analysis['probability_of_doxxing'])))
            
            # Add confidence field for backward compatibility
            analysis['confidence'] = analysis.get('probability_of_doxxing', 0.0)
            
            return analysis
            
        except Exception as e:
            print(f"❌ Error calling Gemini: {e}")
            return {
                "is_doxxing": False,
                "probability_of_doxxing": 0.0,
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
        
        # Extract key information - support both probability_of_doxxing and confidence
        confidence = float(self.analysis.get('probability_of_doxxing', self.analysis.get('confidence', 0)))
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
    **📊 Probability:** {confidence * 100}%
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
            foo, risk_number = self._get_risk_values(risk_level.lower(), 0)
            embed = discord.Embed(
                title=f"Post Automatically Removed for Doxxing: {risk_level} Risk",
                timestamp=datetime.now() # Timestamp of when the report was initiated
            )
        
            embed.add_field(name="**Victim Name**", value=f"```{who_doxxed}```", inline=False)
            embed.add_field(name="**Author of Reported Message**", value=f"{self.message.author.mention} (`{self.message.author.name}`, ID: `{self.message.author.id}`)", inline=True)

            # If Doxxing info types were collected, add them to the embed
            embed.add_field(name="**Doxxing Information Types Reported**", value=', '.join(info_types) if info_types else 'Various personal details', inline=False)
                
            embed.add_field(name="**Harm Assessment**", value=harm_level.title(), inline=False)

            embed.add_field(name="**Result**", value="✅ **Automatic Action Taken:** Message deleted and user notified.", inline=False)
                        
            return embed, bot_report.strip(), risk_number, confidence, None
        
        # Medium confidence: post will be sent for manual review
        if confidence >= 0.7:
            doxxing_score = 0
            if who_doxxed != "Unknown":
                doxxing_score = victim_score(who_doxxed)

            embed_color, risk_number = self._get_risk_values(risk_level.lower(), doxxing_score)

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

            embed.add_field(name="**Doxxing Information Types Reported**", value=', '.join(info_types) if info_types else 'Various personal details', inline=False)
                
            embed.add_field(name="**Harm Assessment**", value=harm_level.title(), inline=True)
            embed.add_field(name="**Risk Level**", value=risk_number, inline=True)
                
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
        if risk == "minimal" or (doxxing_score > 0 and doxxing_score < 10):
            color = 0x3498db   # Blue
        elif risk == "low" or doxxing_score < 30:
            color = 0xf1c40f   # Yellow
        elif risk == "medium" or doxxing_score < 50:
            color = 0xe67e22   # Orange
        elif risk == "high" or doxxing_score > 0:
            color = 0xe74c3c   # Red
        if risk == "minimal":
            number = 1
        elif risk == "Low":
            number = 2
        elif risk == "medium":
            number = 3
        elif risk == "high":
            number = 4
        return color, number  # Grey (default/unknown)
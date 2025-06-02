# gemini_detector.py
import json
import os
import vertexai
from vertexai.generative_models import GenerativeModel

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

MEDIUM-RISK PRIVACY CONCERNS:
• Partial personal information that could enable targeting
• Professional info shared with malicious context
• Location data that narrows down private residence
• Social media accounts of private individuals
• Information that enables further stalking/harassment

CONTEXTUAL ANALYSIS PRIORITIES:
1. CONSENT: Did the person consent to this information being shared?
2. INTENT: Is this meant to help or harm the target?
3. SPECIFICITY: How precise is the identifying information?
4. VULNERABILITY: Is the target in a vulnerable position?
5. ESCALATION: Does this fit a pattern of increasing harassment?

ADVANCED PATTERN RECOGNITION:
• Look for coded language or euphemisms for doxxing
• Detect "breadcrumb" doxxing (small details that accumulate)
• Identify coordinated harassment indicators
• Recognize victim-blaming or justification narratives
• Spot "just asking questions" that seek personal info

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
• Public figures: Already public info may be less concerning
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

PARTIAL INFORMATION ACCUMULATION:
• Message 1: "This guy in my math class is annoying"
• Message 2: "He drives a blue Honda"  
• Message 3: "His name starts with J"
• Message 4: "He works at the pizza place on Main Street"
(CONCERNING PATTERN - breadcrumb doxxing building identifying profile)

=== RESPONSE REQUIREMENTS ===

For "who_was_doxxed": Be specific - "John Smith, a local teacher" not just "someone"
For "sensitive_details": List exact items found - "home address: 123 Oak St, phone: 555-0123"
For "reasoning": Give thorough analysis - explain your decision-making process step by step
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
        "who_was_doxxed": "Specific name and description - be detailed about who this person is",
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
    
    def format_detailed_report(self, analysis):
        """Format the detailed doxxing analysis for display"""
        
        if not analysis.get('is_doxxing', False):
            return None
        
        # Extract key information
        confidence = int(analysis.get('confidence', 0) * 100)
        risk_level = analysis.get('risk_level', 'UNKNOWN')
        
        # Target information
        target_info = analysis.get('target_analysis', {})
        who_doxxed = target_info.get('who_was_doxxed', 'Unknown person')
        relationship = target_info.get('relationship_to_author', 'unknown')
        
        # What information was shared
        info_disclosed = analysis.get('information_disclosed', {})
        info_types = info_disclosed.get('info_types_found', [])
        sensitive_details = info_disclosed.get('sensitive_details', [])
        
        # Context and intent
        context = analysis.get('context_analysis', {})
        intent = context.get('apparent_intent', 'unclear')
        harm_level = context.get('potential_harm_level', 'unknown')
        
        # Moderator summary
        mod_summary = analysis.get('moderator_summary', {})
        primary_concern = mod_summary.get('primary_concern', 'Privacy violation detected')
        reasoning = mod_summary.get('reasoning', 'No detailed reasoning provided')
        action = mod_summary.get('recommended_action', 'review_needed')
        
        # Format the report
        report = f"""
    **🚨 DOXXING DETECTED - {risk_level} RISK**

    **👤 Target:** {who_doxxed} ({relationship} to author)
    **📊 Confidence:** {confidence}%
    **⚠️ Primary Concern:** {primary_concern}

    **📋 Information Exposed:**
    • Types: {', '.join(info_types) if info_types else 'Various personal details'}
    • Sensitive Details: {', '.join(sensitive_details) if sensitive_details else 'See message content'}

    **🎯 Context Analysis:**
    • Intent: {intent.title()}
    • Harm Level: {harm_level.title()}

    **🤖 AI Analysis:** {reasoning}

    **✅ Recommended Action:** {action.replace('_', ' ').title()}
        """
        
        return report.strip()
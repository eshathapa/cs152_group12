# gemini_detector.py
import json
import os
import anthropic
import discord
from datetime import datetime
from supabase_helper import victim_score

token_path = 'tokens.json'
if not os.path.isfile(token_path):
    raise Exception(f"{token_path} not found!")
with open(token_path) as f:
    tokens = json.load(f)
    anthropic_key = tokens['anthropic']

class ClaudeDoxxingDetector:
    def __init__(self):        
        # Load Anthropic model
        self.model = anthropic.Anthropic(api_key=anthropic_key)
        
        print(f"✅ Anthropic detector initialized")
    
    def analyze_for_doxxing(self, message_content: str, author_name: str = "Unknown"):
        """
        Analyze a Discord message for doxxing using Gemini AI
        """
        try:
            # Call Claude
            response = self.model.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                system=[
                {
                    "type": "text",
                    "text": """You are a content moderator with experience in detecting doxxing, harassment, and privacy violations across social platforms. You understand the nuanced difference between legitimate information sharing and malicious doxxing.

You will receive messages in the following format

AUTHOR: [Author]
MESSAGE: "[Message Content]"

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
{
    "is_doxxing": true/false,
    "probability_of_doxxing": 0.85,
    "risk_level": "HIGH/MEDIUM/LOW/MINIMAL",
    "target_analysis": {
        "who_was_doxxed": "Full name of the person who was doxxed. If you do not know, say 'Unknown'",
        "relationship_to_author": "self/friend/stranger/enemy/unknown - include any context about their relationship",
        "is_public_figure": true/false,
        "apparent_consent": "explicit/implied/none/unknown - explain what indicates consent level"
    },
    "information_disclosed": {
        "info_types_found": ["real_name", "address", "phone", "email", "workplace", "family_info", "financial", "government_id", "social_media", "photos"],
        "specificity_level": "exact/approximate/vague - describe how precise the information is",
        "sensitive_details": ["List every specific sensitive item found with exact details where possible"],
        "partial_info": "Detailed description of incomplete but concerning information that could enable further doxxing"
    },
    "moderator_summary": {
        "primary_concern": "Detailed one-line summary explaining the main risk and why it matters",
        "immediate_risks": ["Comprehensive list of specific immediate dangers to the target"],
        "reasoning": "Thorough step-by-step analysis: What information was shared? Why is it concerning? What context clues inform your probability assessment? What harm could result? Why this probability level?",
        "recommended_action": "remove_immediately/warn_user/monitor_closely/no_action_needed - with brief justification",
        "follow_up_needed": "Specific actionable steps: monitor patterns, check for coordination, verify target identity, escalate to authorities, etc."
    }
}""",
                    "cache_control": {"type": "ephemeral"}
                },
                ],
                messages=[{"role": "user", "content": f'Analyze the following post:\nAUTHOR: {author_name}\nMESSAGE CONTENT: "{message_content}".'}],
            )
            
            print(response.usage.model_dump_json())

            try:
                # Clean up response
                result_text = str(response.content[0].text).strip()
                if '```json' in result_text:
                    result_text = result_text.split('```json')[1].split('```')[0].strip()
                elif '```' in result_text:
                    result_text = result_text.split('```')[1].strip()
                
                opening = self.findnth(result_text, "{", 1)
                closing = self.findnth(result_text, "}", 4)

                result_text = result_text[opening:closing + 1]
                
                # Parse JSON
                analysis = json.loads(result_text)
                
                # Ensure confidence is between 0 and 1
                if 'probability_of_doxxing' in analysis:
                    analysis['probability_of_doxxing'] = max(0.0, min(1.0, float(analysis['probability_of_doxxing'])))
                
                return analysis
            except Exception as e:
                with open("missed.txt", "a") as f:
                    f.write(response.content[0].text + "\n\n")
                print("Added to missed.txt")
                return None
            
        except Exception as e:
            print(f"❌ Error calling Claude: {e}")
            return {
                "is_doxxing": False,
                "probability_of_doxxing": 0.0,
                "reasoning": f"Analysis failed: {str(e)}"
            }

    def findnth(self, haystack, needle, n):
        start = haystack.find(needle, 0)
        for i in range(n - 1):
            if start == -1 or start > len(haystack):
                return -1
            next_needle = haystack.find(needle, start + 1)
            start = next_needle
        return start
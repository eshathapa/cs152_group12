# test_connection.py - Quick test to verify Google Cloud connection
import json
from gemini_detector import GeminiDoxxingDetector

def test_connection():
    print("🚀 Testing Google Cloud + Gemini Connection")
    print("=" * 50)
    
    # 1. Check tokens.json
    try:
        with open('tokens.json', 'r') as f:
            tokens = json.load(f)
        print("✅ tokens.json loaded")
        print(f"   Project ID: {tokens.get('google_project_id', 'MISSING')}")
        print(f"   Location: {tokens.get('google_location', 'MISSING')}")
    except Exception as e:
        print(f"❌ Failed to load tokens.json: {e}")
        return False
    
    # 2. Check credentials file
    import os
    if os.path.exists('google-credentials.json'):
        print("✅ google-credentials.json found")
    else:
        print("❌ google-credentials.json not found")
        return False
    
    # 3. Test Gemini detector
    try:
        print("\n🤖 Initializing Gemini detector...")
        detector = GeminiDoxxingDetector(
            project_id=tokens['google_project_id'],
            location=tokens.get('google_location', 'us-central1')
        )
        print("✅ Gemini detector initialized")
    except Exception as e:
        print(f"❌ Failed to initialize Gemini: {e}")
        return False
    
    # 4. Test actual API call
    try:
        print("\n🧪 Testing API call with simple message...")
        result = detector.analyze_for_doxxing("Kill this Lady at 459 Lagunita drive, Anna Morchild", "TestUser")
        
        print("✅ API call successful!")
        print(f"   Result: {'Doxxing detected' if result['is_doxxing'] else 'No doxxing'}")
        print(f"   Confidence: {result.get('confidence', 0):.0%}")
        print(f"   Reasoning: {result.get('reasoning', 'No reasoning')}")
        
        return True
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    if success:
        print("\n🎉 Everything is connected and working!")
        print("Ready to integrate with your Discord bot.")
    else:
        print("\n💔 Something isn't working. Check the errors above.")

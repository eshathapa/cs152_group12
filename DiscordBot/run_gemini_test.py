import json
from gemini_detector import GeminiDoxxingDetector

detector = GeminiDoxxingDetector("milestone3trustandsafety")

correct = 0
total = 0

with open("doxxing_test_dataset.jsonl", "r") as f:
    for line in f:
        case = json.loads(line)
        author = case["author"]
        message = case["message"]
        expected = case["expected"]["is_doxxing"]

        try:
            result = detector.analyze_for_doxxing(message, author_name=author)
            actual = result.get("is_doxxing", None)

            if actual == expected:
                correct += 1
            else:
                print(f"❌ Mismatch on: {message}")
                print(f"   Expected: {expected}, Got: {actual}")
        except Exception as e:
            print(f"❌ Error analyzing: {message}")
            print(e)

        total += 1

accuracy = correct / total * 100 if total > 0 else 0
print(f"✅ Accuracy: {accuracy:.2f}% ({correct}/{total})")

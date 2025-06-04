import json
from gemini_detector import GeminiDoxxingDetector

detector = GeminiDoxxingDetector("milestone3trustandsafety")

correct = 0
true_pos = 0
false_pos = 0
true_neg = 0
false_neg = 0
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
                if actual:
                    true_pos += 1
                else:
                    true_neg += 1
            else:
                if actual:
                    false_neg += 1
                else:
                    false_pos += 1
                print(f"❌ Mismatch on: {message}")
                print(f"   Expected: {expected}, Got: {actual}")
        except Exception as e:
            print(f"❌ Error analyzing: {message}")
            print(e)

        total += 1

accuracy = correct / total * 100 if total > 0 else 0
precision = true_pos / (true_pos + false_pos)
recall = true_pos / (true_pos + false_neg)
f1 = 2 * precision * recall / (precision + recall)
print(f"✅ Accuracy: {accuracy:.2f} ({correct}/{total})")
print(f"✅ Precision: {precision:.2f} ({true_pos}/{true_pos + false_pos})")
print(f"✅ Recall: {recall:.2f} ({true_pos}/{true_pos + false_pos})")
print(f"F1 Score: {f1}")


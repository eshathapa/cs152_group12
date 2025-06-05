import json
from claude_detector import ClaudeDoxxingDetector
from datetime import datetime

detector = ClaudeDoxxingDetector()
count = 1

print("Starting at: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

with open("claude_output.txt", "w") as output:
    with open("doxxing_test_dataset.jsonl", "r") as f:
        for line in f:
            case = json.loads(line)
            author = case["author"]
            message = case["message"]
            expected = case["expected"]["is_doxxing"]

            print(expected)
            
            print(f"Entry {count}")
            try:
                result = detector.analyze_for_doxxing(message, author_name=author)
                actual = result.get("probability_of_doxxing", None)
                to_write = f"{message}|{expected}|{actual}\n"
                output.write(to_write)
            except Exception as e:
                print(f"❌ Error analyzing: {message}")
                print(e)
            
            count += 1

print("Ending at: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

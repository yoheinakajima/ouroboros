#!/usr/bin/env python3
"""Verify all test cases match expected outputs."""
import json
import subprocess
import sys

test_cases = [
    {
        "name": "test_basic_sentence",
        "input": {"sentence": "The quick brown fox jumps"},
        "expected": {"word_count": 5, "unique_words": 5, "longest_word": "quick"}
    },
    {
        "name": "test_repeated_words",
        "input": {"sentence": "hello world hello"},
        "expected": {"word_count": 3, "unique_words": 2, "longest_word": "hello"}
    },
    {
        "name": "test_case_insensitive",
        "input": {"sentence": "Hello HELLO hello"},
        "expected": {"word_count": 3, "unique_words": 1, "longest_word": "Hello"}
    },
    {
        "name": "test_empty_sentence",
        "input": {"sentence": ""},
        "expected": {"word_count": 0, "unique_words": 0, "longest_word": ""}
    },
    {
        "name": "test_whitespace_only",
        "input": {"sentence": "   "},
        "expected": {"word_count": 0, "unique_words": 0, "longest_word": ""}
    },
    {
        "name": "test_single_word",
        "input": {"sentence": "supercalifragilisticexpialidocious"},
        "expected": {"word_count": 1, "unique_words": 1, "longest_word": "supercalifragilisticexpialidocious"}
    },
    {
        "name": "test_multiple_spaces",
        "input": {"sentence": "one  two   three"},
        "expected": {"word_count": 3, "unique_words": 3, "longest_word": "three"}
    },
    {
        "name": "test_with_punctuation",
        "input": {"sentence": "Hello, world!"},
        "expected": {"word_count": 2, "unique_words": 2, "longest_word": "Hello,"}
    }
]

all_passed = True
for test in test_cases:
    result = subprocess.run(
        ["python", "agent.py"],
        input=json.dumps(test["input"]),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ {test['name']}: Non-zero exit code {result.returncode}")
        all_passed = False
        continue
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ {test['name']}: Invalid JSON output: {e}")
        all_passed = False
        continue
    
    if output == test["expected"]:
        print(f"✅ {test['name']}: PASS")
    else:
        print(f"❌ {test['name']}: FAIL")
        print(f"   Expected: {test['expected']}")
        print(f"   Got:      {output}")
        all_passed = False

if all_passed:
    print("\n🎉 All tests passed!")
    sys.exit(0)
else:
    print("\n❌ Some tests failed")
    sys.exit(1)

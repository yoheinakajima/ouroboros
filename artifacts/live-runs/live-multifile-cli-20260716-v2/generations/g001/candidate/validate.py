#!/usr/bin/env python3
"""
Validation script to verify all functionality works correctly.
"""

import subprocess
import json
import sys


def test_cli(input_text, expected):
    """Test the CLI with given input and expected output."""
    result = subprocess.run(
        ['python', 'main.py'],
        input=input_text,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"FAIL: Exit code {result.returncode} for input: {repr(input_text)}")
        print(f"  stderr: {result.stderr}")
        return False
    
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"FAIL: Invalid JSON for input: {repr(input_text)}")
        print(f"  stdout: {result.stdout}")
        return False
    
    for key, value in expected.items():
        if key not in output:
            print(f"FAIL: Missing key '{key}' for input: {repr(input_text)}")
            return False
        if output[key] != value:
            print(f"FAIL: Expected {key}={value}, got {output[key]} for input: {repr(input_text)}")
            return False
    
    return True


def main():
    """Run all validation tests."""
    tests = [
        ("The quick brown fox jumps", {"word_count": 5, "unique_words": 5, "longest_word": "quick"}),
        ("hello world hello", {"word_count": 3, "unique_words": 2, "longest_word": "hello"}),
        ("Hello HELLO hello World", {"word_count": 4, "unique_words": 2}),
        ("", {"word_count": 0, "unique_words": 0, "longest_word": ""}),
        ("   \n  \t  ", {"word_count": 0, "unique_words": 0, "longest_word": ""}),
        ("supercalifragilisticexpialidocious", {"word_count": 1, "unique_words": 1}),
        ("Hello, world! How are you?", {"word_count": 5, "unique_words": 5, "longest_word": "Hello,"}),
        ("one    two     three", {"word_count": 3, "unique_words": 3, "longest_word": "three"}),
    ]
    
    passed = 0
    failed = 0
    
    for input_text, expected in tests:
        if test_cli(input_text, expected):
            passed += 1
            print(f"PASS: {repr(input_text[:30])}")
        else:
            failed += 1
    
    print(f"\n{passed} passed, {failed} failed")
    
    if failed > 0:
        sys.exit(1)
    
    print("\nAll validation tests passed!")


if __name__ == "__main__":
    main()

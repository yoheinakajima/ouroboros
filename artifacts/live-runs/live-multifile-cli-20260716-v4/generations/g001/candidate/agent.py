#!/usr/bin/env python3
"""
JSON-stdin CLI for sentence analysis.
Reads JSON from stdin, analyzes the sentence, and outputs JSON to stdout.
"""
import json
import sys
from main import analyze_sentence


def main():
    """Main entry point for the CLI."""
    try:
        # Read JSON from stdin
        input_data = json.loads(sys.stdin.read() or "{}")
        
        # Extract sentence from input
        sentence = input_data.get("sentence", "")
        
        # Analyze the sentence
        result = analyze_sentence(sentence)
        
        # Output JSON to stdout
        print(json.dumps(result))
        
        sys.exit(0)
    except Exception as e:
        # Handle errors gracefully
        error_result = {
            "error": str(e),
            "word_count": 0,
            "unique_words": 0,
            "longest_word": ""
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()

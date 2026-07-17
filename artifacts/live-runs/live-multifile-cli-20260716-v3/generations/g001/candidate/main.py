#!/usr/bin/env python3
"""
Main entrypoint for the sentence analyzer CLI.
Reads a sentence from stdin and outputs JSON analysis to stdout.
"""

import sys
import json
from text_analyzer import analyze_sentence


def main():
    """
    Main function that reads from stdin and outputs JSON analysis.
    """
    try:
        # Read input from stdin (plain text, not JSON)
        input_text = sys.stdin.read()
        
        # Analyze the sentence
        result = analyze_sentence(input_text)
        
        # Output as JSON
        print(json.dumps(result))
        
        return 0
        
    except Exception as e:
        # Error handling - output error as JSON
        error_result = {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": "",
            "error": str(e)
        }
        print(json.dumps(error_result), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

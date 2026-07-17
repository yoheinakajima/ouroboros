#!/usr/bin/env python3
"""
Main CLI entry point for sentence analyzer.

Reads a sentence from stdin and outputs JSON analysis to stdout.
"""

import sys
import json
from analyzer import analyze_sentence


def main():
    """
    Main entry point for the CLI.
    
    Reads input from stdin, analyzes it, and outputs JSON to stdout.
    """
    try:
        # Read input from stdin
        input_text = sys.stdin.read()
        
        # Analyze the sentence
        result = analyze_sentence(input_text)
        
        # Output JSON to stdout
        print(json.dumps(result))
        
        # Exit successfully
        sys.exit(0)
        
    except Exception as e:
        # In case of error, output error information as JSON
        error_result = {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": "",
            "error": str(e)
        }
        print(json.dumps(error_result))
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Main CLI entrypoint for sentence analyzer.
Reads a sentence from stdin and outputs JSON analysis to stdout.
"""

import sys
import json
from analyzer import analyze_sentence

def main():
    """
    Read sentence from stdin, analyze it, and output JSON results.
    """
    try:
        # Read input from stdin
        sentence = sys.stdin.read()
        
        # Analyze the sentence
        result = analyze_sentence(sentence)
        
        # Output JSON to stdout
        print(json.dumps(result))
        
        # Exit successfully
        sys.exit(0)
        
    except Exception as e:
        # In case of error, output error message to stderr and exit with error code
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()

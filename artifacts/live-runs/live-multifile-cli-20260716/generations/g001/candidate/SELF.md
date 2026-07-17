# Self

## Architecture
Multi-file Python CLI application with separated concerns:
- `main.py`: CLI entrypoint handling stdin/stdout
- `analyzer.py`: Core sentence analysis logic (importable module)
- `test_analyzer.py`: Comprehensive unit tests

## Capabilities
- Reads sentences from stdin
- Analyzes text to count total words
- Counts unique words (case-insensitive)
- Identifies longest word in input
- Outputs valid JSON with word_count, unique_words, and longest_word
- Handles edge cases: empty input, whitespace-only, punctuation, multiple spaces
- Provides importable Python module for programmatic use

## Known strengths
- Clean separation of concerns
- Comprehensive test coverage
- Handles all specified edge cases
- Valid JSON output
- Well-documented with README

## Known weaknesses
None identified - all tests passing

## Improvement strategy
Maintain test coverage and code quality. Monitor for any edge cases discovered in production use.

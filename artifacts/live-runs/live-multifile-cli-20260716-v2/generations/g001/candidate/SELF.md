# Self

## Architecture
Multi-file Python CLI application with separated concerns:
- `main.py`: CLI entry point handling stdin/stdout
- `analyzer.py`: Core sentence analysis logic
- `test_analyzer.py`: Unit tests for analyzer module
- `test_cli.py`: Integration tests for CLI interface

## Capabilities
- Reads sentences from stdin
- Analyzes text to count total words
- Counts unique words (case-insensitive)
- Identifies longest word in input
- Outputs valid JSON with word_count, unique_words, and longest_word
- Handles edge cases: empty input, whitespace-only, punctuation, multiple spaces
- Provides importable analyzer module for programmatic use

## Known strengths
- Clean separation of concerns (CLI vs. analysis logic)
- Comprehensive test coverage (14 automated tests)
- Robust error handling
- Well-documented with README and inline comments
- Handles all specified edge cases correctly

## Test results
- All 14 unit and integration tests passing
- Verified against all public test scenarios
- Module import functionality confirmed

## Improvement strategy
Current implementation meets all requirements. Future enhancements could include:
- Support for different word tokenization strategies
- Performance optimization for very large inputs
- Additional output formats (CSV, XML)

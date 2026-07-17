# Self

## Architecture
Multi-file Python CLI application with clear separation of concerns:
- **main.py**: Entry point handling stdin/stdout
- **text_analyzer.py**: Core analysis logic module
- **test_analyzer.py**: Automated unit tests

## Capabilities
Analyzes sentences from stdin and outputs JSON with:
- word_count: Total number of words
- unique_words: Count of distinct words (case-insensitive)
- longest_word: The longest word in the input

Handles edge cases including empty input, whitespace-only input, punctuation, and case variations.

## Known strengths
- Clean multi-file architecture
- Comprehensive error handling
- Automated test suite with 8 passing tests
- Proper punctuation handling via regex cleaning
- Case-insensitive unique word counting

## Implementation details
- Words are split by whitespace
- Punctuation is stripped using regex
- Returns valid JSON for all inputs
- Exit code 0 on success

## Test coverage
All unit tests pass. Manual testing confirms correct behavior for:
- Basic sentences
- Repeated words
- Case variations
- Empty input
- Whitespace-only input
- Single words
- Punctuation handling

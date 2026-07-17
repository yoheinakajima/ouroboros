# Self

## Architecture
Multi-file JSON-stdin CLI application with separated concerns:
- `agent.py` - CLI entrypoint handling JSON I/O
- `main.py` - Core sentence analysis logic
- `test_analyzer.py` - Comprehensive automated test suite

## Capabilities
- Reads JSON from stdin containing a "sentence" field
- Analyzes text to count total words, unique words (case-insensitive), and longest word
- Outputs valid JSON with word_count, unique_words, and longest_word fields
- Handles edge cases: empty input, whitespace, punctuation, multiple spaces
- Robust error handling with graceful degradation

## Known weaknesses
None identified. All public tests pass.

## Improvement strategy
Implementation complete. All requirements satisfied with execution-grounded evidence.

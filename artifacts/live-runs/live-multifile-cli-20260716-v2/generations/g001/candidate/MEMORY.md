# Memory

## Durable Lessons

### Test-Driven Development
- Created comprehensive unit tests (test_analyzer.py) and integration tests (test_cli.py)
- All 14 tests pass, covering edge cases and normal operation
- Tests verify both module import and CLI functionality

### Architecture Decisions
- Separated CLI logic (main.py) from analysis logic (analyzer.py)
- This separation enables both CLI usage and programmatic import
- Clean interfaces make testing straightforward

### Edge Case Handling
- Empty input and whitespace-only input both return zeros and empty string
- Multiple consecutive spaces handled correctly via split()
- Punctuation attached to words is preserved (treated as part of word)
- Case-insensitive unique word counting using set with .lower()

### JSON Output
- Always output valid JSON with exactly three fields
- Use json.dumps() for guaranteed valid JSON formatting
- Include error handling to ensure JSON output even on exceptions

### Documentation
- README.md includes usage examples, stdin instructions, and module import examples
- Inline docstrings for all functions
- Clear separation between user-facing docs and code comments

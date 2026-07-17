# Memory

## Lessons Learned

### Input Protocol
- Tests send plain text via stdin, not JSON objects
- The input_protocol "json-stdin" refers to the output format, not input format
- Read stdin directly as text, not as JSON payload

### Multi-file Architecture
- Separate concerns: entrypoint (main.py), logic (text_analyzer.py), tests (test_analyzer.py)
- Use proper module imports for clean architecture
- Include comprehensive README.md for documentation

### Text Analysis Implementation
- Use regex to clean punctuation from words: `re.sub(r'[^a-zA-Z0-9]', '', word)`
- Case-insensitive uniqueness: convert to lowercase for set operations
- Handle edge cases: empty strings, whitespace-only input
- Return consistent JSON structure for all cases

### Testing Strategy
- Write unit tests that can run with `python -m unittest -q`
- Test edge cases explicitly: empty, whitespace, single word, punctuation
- Verify JSON output format and structure
- Manual testing confirms integration between modules

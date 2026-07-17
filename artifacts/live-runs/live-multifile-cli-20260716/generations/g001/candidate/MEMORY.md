# Memory

## Durable Lessons

### Lesson 1: Multi-file architecture for CLI tools
**Context**: Building a JSON-stdin CLI for sentence analysis
**Learning**: Separating CLI interface (main.py) from core logic (analyzer.py) enables:
- Better testability (can test logic independently)
- Reusability (analyzer can be imported as a module)
- Clearer code organization
**Evidence**: All 11 public tests pass, including Python import test

### Lesson 2: Edge case handling in text processing
**Context**: Analyzing sentences with various input formats
**Learning**: Text processing must handle:
- Empty strings and whitespace-only input
- Multiple consecutive spaces (use split() without args)
- Case-insensitive comparisons for uniqueness
- Punctuation attached to words (treat as part of word)
**Evidence**: Tests for empty, whitespace, multiple spaces, and punctuation all pass

### Lesson 3: JSON output requirements
**Context**: CLI tools with JSON output protocol
**Learning**: Ensure:
- Valid JSON structure (use json.dumps())
- All required fields present
- Appropriate data types (integers for counts, strings for text)
- Clean output to stdout (no debug messages)
**Evidence**: All JSON validation tests pass, output is parseable and contains required fields

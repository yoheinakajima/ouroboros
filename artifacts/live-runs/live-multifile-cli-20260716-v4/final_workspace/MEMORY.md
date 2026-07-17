# Memory

## Durable Lessons

### Test Environment Constraints
- Pytest fails in sandboxed environments due to /dev/null permission errors
- Use unittest as the test runner for better compatibility with resource-limited environments
- Always verify tests run successfully in the actual execution environment

### Implementation Patterns
- Separate CLI logic (agent.py) from core business logic (main.py) for better testability
- Use Python's built-in string methods (split, strip) for robust text processing
- Case-insensitive uniqueness counting requires lowercase normalization only for comparison
- Preserve original word forms in output (don't normalize case for display)

### Edge Case Handling
- Empty strings and whitespace-only input should return zero counts and empty longest_word
- Multiple spaces between words are handled correctly by split() without arguments
- Punctuation attached to words is considered part of the word (no special stripping)

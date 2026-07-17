# Sentence Analyzer CLI

A JSON-stdin command-line tool that analyzes sentences and returns word statistics.

## Features

- Counts total words in a sentence
- Counts unique words (case-insensitive)
- Identifies the longest word
- Handles edge cases: empty input, whitespace, punctuation, multiple spaces

## Usage

The CLI reads JSON from stdin and writes JSON to stdout.

### Input Format

```json
{
  "sentence": "Your sentence here"
}
```

### Output Format

```json
{
  "word_count": 5,
  "unique_words": 5,
  "longest_word": "sentence"
}
```

### Example

```bash
echo '{"sentence": "The quick brown fox jumps"}' | python agent.py
```

Output:
```json
{"word_count": 5, "unique_words": 5, "longest_word": "quick"}
```

## Implementation Details

- **Word Separation**: Words are separated by whitespace
- **Unique Counting**: Case-insensitive (e.g., "Hello" and "hello" count as one unique word)
- **Longest Word**: Returns the original form (preserves case and punctuation)
- **Punctuation**: Attached punctuation is considered part of the word
- **Empty Input**: Returns `word_count=0`, `unique_words=0`, `longest_word=""`

## Running Tests

Run the automated test suite:

```bash
python -m pytest test_analyzer.py -v
```

Or using unittest:

```bash
python -m unittest test_analyzer.py -v
```

## Project Structure

- `agent.py` - Main CLI entrypoint
- `main.py` - Core sentence analysis logic
- `test_analyzer.py` - Automated test suite
- `README.md` - This file
- `ouroboros.json` - Configuration metadata

## Requirements

- Python 3.6+
- No external dependencies for core functionality
- pytest (optional, for running tests)

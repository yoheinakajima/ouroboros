# Sentence Analyzer CLI

A command-line tool that analyzes sentences and provides word statistics in JSON format.

## Features

- Count total words in a sentence
- Count unique words (case-insensitive)
- Find the longest word
- Handle edge cases (empty input, multiple spaces, punctuation)

## Usage

The tool reads input from stdin and outputs JSON to stdout.

### Basic Usage

```bash
echo "The quick brown fox jumps" | python main.py
```

Output:
```json
{"word_count": 5, "unique_words": 5, "longest_word": "quick"}
```

### Using stdin redirection

```bash
python main.py < input.txt
```

### Interactive mode

```bash
python main.py
# Type your sentence and press Ctrl+D (Unix) or Ctrl+Z (Windows)
```

## Output Format

The tool outputs valid JSON with three fields:

- `word_count` (integer): Total number of words in the input
- `unique_words` (integer): Count of distinct words (case-insensitive)
- `longest_word` (string): The longest word found; if multiple words tie, one is returned

## Examples

### Simple sentence
```bash
echo "hello world" | python main.py
```
Output: `{"word_count": 2, "unique_words": 2, "longest_word": "hello"}`

### Repeated words
```bash
echo "hello world hello" | python main.py
```
Output: `{"word_count": 3, "unique_words": 2, "longest_word": "hello"}`

### Case-insensitive unique counting
```bash
echo "Hello HELLO hello World" | python main.py
```
Output: `{"word_count": 4, "unique_words": 2, "longest_word": "Hello"}`

### Empty input
```bash
echo "" | python main.py
```
Output: `{"word_count": 0, "unique_words": 0, "longest_word": ""}`

### Punctuation handling
Punctuation attached to words is considered part of the word:
```bash
echo "Hello, world!" | python main.py
```
Output: `{"word_count": 2, "unique_words": 2, "longest_word": "Hello,"}`

## Module Usage

The analyzer can also be imported and used as a Python module:

```python
from analyzer import analyze_sentence

result = analyze_sentence("The quick brown fox")
print(result)
# {'word_count': 4, 'unique_words': 4, 'longest_word': 'quick'}
```

## Implementation Details

- Words are separated by whitespace (spaces, tabs, newlines)
- Multiple consecutive spaces are handled correctly
- Punctuation attached to words is preserved
- Unique word counting is case-insensitive
- Empty or whitespace-only input returns zeros and empty string

## Files

- `main.py` - CLI entry point
- `analyzer.py` - Core analysis logic
- `README.md` - This file

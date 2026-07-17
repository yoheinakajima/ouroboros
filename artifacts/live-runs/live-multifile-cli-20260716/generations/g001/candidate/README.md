# Sentence Analyzer CLI

A command-line tool that analyzes sentences and provides word statistics in JSON format.

## Features

- Counts total words in a sentence
- Counts unique words (case-insensitive)
- Identifies the longest word
- Handles edge cases (empty input, multiple spaces, punctuation)

## Usage

The tool reads input from stdin and outputs JSON to stdout.

### Basic usage:

```bash
echo "The quick brown fox jumps" | python main.py
```

Output:
```json
{"word_count": 5, "unique_words": 5, "longest_word": "quick"}
```

### Using with a file:

```bash
cat sentence.txt | python main.py
```

### Interactive usage:

```bash
python main.py
# Type your sentence and press Ctrl+D (Unix) or Ctrl+Z (Windows)
```

## Output Format

The tool outputs valid JSON with three fields:

- `word_count` (integer): Total number of words in the input
- `unique_words` (integer): Count of distinct words (case-insensitive comparison)
- `longest_word` (string): The longest word found; empty string if no words

## Examples

### Simple sentence:
```bash
echo "hello world" | python main.py
# {"word_count": 2, "unique_words": 2, "longest_word": "hello"}
```

### Repeated words:
```bash
echo "hello world hello" | python main.py
# {"word_count": 3, "unique_words": 2, "longest_word": "hello"}
```

### Case-insensitive unique counting:
```bash
echo "Hello HELLO hello World" | python main.py
# {"word_count": 4, "unique_words": 2, "longest_word": "Hello"}
```

### Empty input:
```bash
echo "" | python main.py
# {"word_count": 0, "unique_words": 0, "longest_word": ""}
```

## Implementation

The tool is split into two main components:

- `main.py`: CLI interface that handles stdin/stdout
- `analyzer.py`: Core analysis logic (can be imported as a module)

## Module Usage

You can also import and use the analyzer module directly in Python:

```python
from analyzer import analyze_sentence

result = analyze_sentence("The quick brown fox")
print(result)
# {'word_count': 4, 'unique_words': 4, 'longest_word': 'quick'}
```

## Requirements

- Python 3.6 or higher
- No external dependencies

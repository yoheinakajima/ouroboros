# Sentence Analyzer CLI

A multi-file Python CLI application that analyzes sentences and returns word statistics in JSON format.

## Features

- Counts total words in a sentence
- Counts unique words (case-insensitive)
- Identifies the longest word
- Handles punctuation gracefully
- Returns results as valid JSON

## Architecture

The application is organized into multiple modules:

- **main.py**: Entry point that handles stdin/stdout and orchestrates the analysis
- **text_analyzer.py**: Core analysis logic for processing sentences
- **test_analyzer.py**: Automated unit tests for the analyzer module

## Usage

### Basic Usage

```bash
echo "The quick brown fox jumps" | python main.py
```

Output:
```json
{"word_count": 5, "unique_words": 5, "longest_word": "quick"}
```

### Using with JSON Input

The CLI reads plain text from stdin:

```bash
echo "hello world hello" | python main.py
```

Output:
```json
{"word_count": 3, "unique_words": 2, "longest_word": "hello"}
```

### Edge Cases

Empty input:
```bash
echo "" | python main.py
```

Output:
```json
{"word_count": 0, "unique_words": 0, "longest_word": ""}
```

## Running Tests

Run the automated test suite:

```bash
python -m unittest test_analyzer.py -v
```

Or run all tests quietly:

```bash
python -m unittest -q
```

## Output Format

The CLI always outputs valid JSON with three fields:

- `word_count` (integer): Total number of words in the input
- `unique_words` (integer): Number of distinct words (case-insensitive)
- `longest_word` (string): The longest word found (empty string if no words)

## Implementation Details

- Words are separated by whitespace
- Punctuation is stripped from words before analysis
- Unique word counting is case-insensitive
- If multiple words tie for longest, the first occurrence is returned
- Empty or whitespace-only input returns zeros and empty string

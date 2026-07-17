"""
Sentence analyzer module.

Provides functionality to analyze sentences and extract statistics.
"""


def analyze_sentence(sentence):
    """
    Analyze a sentence and return word statistics.
    
    Args:
        sentence (str): The input sentence to analyze
        
    Returns:
        dict: A dictionary containing:
            - word_count: Total number of words
            - unique_words: Count of unique words (case-insensitive)
            - longest_word: The longest word found (or empty string if no words)
    """
    # Handle empty or whitespace-only input
    if not sentence or not sentence.strip():
        return {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": ""
        }
    
    # Split by whitespace to get words
    words = sentence.split()
    
    # Count total words
    word_count = len(words)
    
    # Count unique words (case-insensitive)
    unique_words = len(set(word.lower() for word in words))
    
    # Find longest word
    longest_word = max(words, key=len) if words else ""
    
    return {
        "word_count": word_count,
        "unique_words": unique_words,
        "longest_word": longest_word
    }

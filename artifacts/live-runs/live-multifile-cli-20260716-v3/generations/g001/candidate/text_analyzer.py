"""
Text analysis module for sentence processing.
Provides functions to analyze word count, unique words, and longest word.
"""

import re


def clean_word(word):
    """
    Remove punctuation from a word, keeping only alphanumeric characters.
    
    Args:
        word: String to clean
        
    Returns:
        Cleaned word string
    """
    return re.sub(r'[^a-zA-Z0-9]', '', word)


def analyze_sentence(sentence):
    """
    Analyze a sentence and return word statistics.
    
    Args:
        sentence: Input sentence string
        
    Returns:
        Dictionary with word_count, unique_words, and longest_word
    """
    if not sentence or not sentence.strip():
        return {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": ""
        }
    
    # Split by whitespace and clean words
    raw_words = sentence.split()
    words = []
    
    for word in raw_words:
        cleaned = clean_word(word)
        if cleaned:  # Only include non-empty words after cleaning
            words.append(cleaned)
    
    if not words:
        return {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": ""
        }
    
    # Calculate word count
    word_count = len(words)
    
    # Calculate unique words (case-insensitive)
    unique_words_set = set(word.lower() for word in words)
    unique_words = len(unique_words_set)
    
    # Find longest word (return first occurrence if tie)
    longest_word = max(words, key=len)
    
    return {
        "word_count": word_count,
        "unique_words": unique_words,
        "longest_word": longest_word
    }

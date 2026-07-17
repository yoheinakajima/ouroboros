#!/usr/bin/env python3
"""
Sentence analyzer module.
Analyzes text to count words, unique words, and find the longest word.
"""


def analyze_sentence(sentence):
    """
    Analyze a sentence and return word statistics.
    
    Args:
        sentence (str): The sentence to analyze
        
    Returns:
        dict: Dictionary containing word_count, unique_words, and longest_word
    """
    if not sentence or not sentence.strip():
        return {
            "word_count": 0,
            "unique_words": 0,
            "longest_word": ""
        }
    
    # Split by whitespace and filter out empty strings
    words = sentence.split()
    words = [w for w in words if w]
    
    # Count total words
    word_count = len(words)
    
    # Count unique words (case-insensitive)
    unique_words = len(set(w.lower() for w in words))
    
    # Find longest word (by original form, not lowercase)
    longest_word = max(words, key=len) if words else ""
    
    return {
        "word_count": word_count,
        "unique_words": unique_words,
        "longest_word": longest_word
    }

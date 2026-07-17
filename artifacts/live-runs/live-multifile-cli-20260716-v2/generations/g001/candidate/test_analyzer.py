"""
Unit tests for the sentence analyzer module.
"""

import unittest
from analyzer import analyze_sentence


class TestAnalyzer(unittest.TestCase):
    """Test cases for the analyze_sentence function."""
    
    def test_basic_sentence(self):
        """Test analysis of a simple sentence with distinct words."""
        result = analyze_sentence("The quick brown fox jumps")
        self.assertEqual(result['word_count'], 5)
        self.assertEqual(result['unique_words'], 5)
        self.assertEqual(result['longest_word'], 'quick')
    
    def test_repeated_words(self):
        """Test handling of repeated words."""
        result = analyze_sentence("hello world hello")
        self.assertEqual(result['word_count'], 3)
        self.assertEqual(result['unique_words'], 2)
        self.assertEqual(result['longest_word'], 'hello')
    
    def test_case_insensitive(self):
        """Test case-insensitive unique word counting."""
        result = analyze_sentence("Hello HELLO hello World")
        self.assertEqual(result['word_count'], 4)
        self.assertEqual(result['unique_words'], 2)
        self.assertIn(result['longest_word'], ['Hello', 'HELLO', 'hello', 'World'])
    
    def test_empty_input(self):
        """Test handling of empty input."""
        result = analyze_sentence("")
        self.assertEqual(result['word_count'], 0)
        self.assertEqual(result['unique_words'], 0)
        self.assertEqual(result['longest_word'], "")
    
    def test_whitespace_only(self):
        """Test handling of whitespace-only input."""
        result = analyze_sentence("   \n  \t  ")
        self.assertEqual(result['word_count'], 0)
        self.assertEqual(result['unique_words'], 0)
        self.assertEqual(result['longest_word'], "")
    
    def test_single_word(self):
        """Test handling of single word input."""
        result = analyze_sentence("supercalifragilisticexpialidocious")
        self.assertEqual(result['word_count'], 1)
        self.assertEqual(result['unique_words'], 1)
        self.assertEqual(result['longest_word'], "supercalifragilisticexpialidocious")
    
    def test_punctuation_attached(self):
        """Test that punctuation is treated as part of words."""
        result = analyze_sentence("Hello, world! How are you?")
        self.assertEqual(result['word_count'], 5)
        self.assertEqual(result['unique_words'], 5)
        self.assertEqual(result['longest_word'], "Hello,")
    
    def test_multiple_spaces(self):
        """Test handling of multiple spaces between words."""
        result = analyze_sentence("one    two     three")
        self.assertEqual(result['word_count'], 3)
        self.assertEqual(result['unique_words'], 3)
        self.assertEqual(result['longest_word'], "three")
    
    def test_longest_word_tie(self):
        """Test that one longest word is returned when there's a tie."""
        result = analyze_sentence("cat dog bat")
        self.assertEqual(result['word_count'], 3)
        self.assertEqual(result['unique_words'], 3)
        self.assertIn(result['longest_word'], ['cat', 'dog', 'bat'])
        self.assertEqual(len(result['longest_word']), 3)
    
    def test_mixed_whitespace(self):
        """Test handling of mixed whitespace characters."""
        result = analyze_sentence("word1\tword2\nword3")
        self.assertEqual(result['word_count'], 3)
        self.assertEqual(result['unique_words'], 3)


if __name__ == '__main__':
    unittest.main()

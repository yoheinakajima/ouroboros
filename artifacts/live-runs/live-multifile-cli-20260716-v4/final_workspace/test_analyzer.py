#!/usr/bin/env python3
"""
Automated tests for the sentence analyzer.
"""
import unittest
from main import analyze_sentence


class TestSentenceAnalyzer(unittest.TestCase):
    """Test cases for sentence analysis functionality."""
    
    def test_basic_sentence(self):
        """Test analysis of a simple sentence with distinct words."""
        result = analyze_sentence("The quick brown fox jumps")
        self.assertEqual(result["word_count"], 5)
        self.assertEqual(result["unique_words"], 5)
        self.assertEqual(result["longest_word"], "quick")
    
    def test_repeated_words(self):
        """Test handling of repeated words."""
        result = analyze_sentence("hello world hello")
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["unique_words"], 2)
        self.assertEqual(result["longest_word"], "hello")
    
    def test_case_insensitive_unique(self):
        """Test that unique word counting is case-insensitive."""
        result = analyze_sentence("Hello HELLO hello")
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["unique_words"], 1)
        # Any of the three forms is acceptable as longest
        self.assertIn(result["longest_word"], ["Hello", "HELLO", "hello"])
    
    def test_empty_sentence(self):
        """Test handling of empty sentence."""
        result = analyze_sentence("")
        self.assertEqual(result["word_count"], 0)
        self.assertEqual(result["unique_words"], 0)
        self.assertEqual(result["longest_word"], "")
    
    def test_whitespace_only(self):
        """Test handling of whitespace-only input."""
        result = analyze_sentence("   ")
        self.assertEqual(result["word_count"], 0)
        self.assertEqual(result["unique_words"], 0)
        self.assertEqual(result["longest_word"], "")
    
    def test_single_word(self):
        """Test handling of single word input."""
        result = analyze_sentence("supercalifragilisticexpialidocious")
        self.assertEqual(result["word_count"], 1)
        self.assertEqual(result["unique_words"], 1)
        self.assertEqual(result["longest_word"], "supercalifragilisticexpialidocious")
    
    def test_multiple_spaces(self):
        """Test handling of multiple spaces between words."""
        result = analyze_sentence("one  two   three")
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["unique_words"], 3)
        self.assertEqual(result["longest_word"], "three")
    
    def test_with_punctuation(self):
        """Test handling of words with attached punctuation."""
        result = analyze_sentence("Hello, world!")
        self.assertEqual(result["word_count"], 2)
        self.assertEqual(result["unique_words"], 2)
        # Punctuation is part of the word
        self.assertEqual(result["longest_word"], "Hello,")
    
    def test_longest_word_tie(self):
        """Test that when multiple words tie for longest, one is returned."""
        result = analyze_sentence("cat dog bat")
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["unique_words"], 3)
        # Any of the three is acceptable
        self.assertIn(result["longest_word"], ["cat", "dog", "bat"])
    
    def test_mixed_case_longest(self):
        """Test that longest word preserves original case."""
        result = analyze_sentence("a BB ccc")
        self.assertEqual(result["word_count"], 3)
        self.assertEqual(result["unique_words"], 3)
        self.assertEqual(result["longest_word"], "ccc")


if __name__ == "__main__":
    unittest.main()

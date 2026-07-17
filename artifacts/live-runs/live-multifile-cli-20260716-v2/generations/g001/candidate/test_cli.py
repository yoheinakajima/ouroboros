"""
Integration tests for the CLI interface.
"""

import unittest
import subprocess
import json


class TestCLI(unittest.TestCase):
    """Test cases for the command-line interface."""
    
    def run_cli(self, input_text):
        """Helper method to run the CLI with given input."""
        result = subprocess.run(
            ['python', 'main.py'],
            input=input_text,
            capture_output=True,
            text=True
        )
        return result
    
    def test_basic_sentence(self):
        """Test CLI with a simple sentence."""
        result = self.run_cli("The quick brown fox jumps")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output['word_count'], 5)
        self.assertEqual(output['unique_words'], 5)
        self.assertEqual(output['longest_word'], 'quick')
    
    def test_repeated_words(self):
        """Test CLI with repeated words."""
        result = self.run_cli("hello world hello")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output['word_count'], 3)
        self.assertEqual(output['unique_words'], 2)
    
    def test_empty_input(self):
        """Test CLI with empty input."""
        result = self.run_cli("")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertEqual(output['word_count'], 0)
        self.assertEqual(output['unique_words'], 0)
        self.assertEqual(output['longest_word'], "")
    
    def test_json_output_format(self):
        """Test that output is valid JSON with required fields."""
        result = self.run_cli("test input")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)
        self.assertIn('word_count', output)
        self.assertIn('unique_words', output)
        self.assertIn('longest_word', output)
        self.assertIsInstance(output['word_count'], int)
        self.assertIsInstance(output['unique_words'], int)
        self.assertIsInstance(output['longest_word'], str)


if __name__ == '__main__':
    unittest.main()

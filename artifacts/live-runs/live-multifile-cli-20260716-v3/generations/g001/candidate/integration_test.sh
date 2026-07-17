#!/bin/bash
# Integration test script for sentence analyzer

echo "Running integration tests..."
echo ""

# Test 1: Basic sentence
echo "Test 1: Basic sentence"
echo "The quick brown fox jumps" | python main.py
echo ""

# Test 2: Repeated words
echo "Test 2: Repeated words"
echo "hello world hello" | python main.py
echo ""

# Test 3: Case insensitive
echo "Test 3: Case insensitive"
echo "Hello HELLO hello" | python main.py
echo ""

# Test 4: Empty input
echo "Test 4: Empty input"
echo "" | python main.py
echo ""

# Test 5: Single word
echo "Test 5: Single word"
echo "supercalifragilisticexpialidocious" | python main.py
echo ""

# Test 6: Punctuation
echo "Test 6: Punctuation handling"
echo "Hello, world! How are you?" | python main.py
echo ""

# Test 7: Whitespace only
echo "Test 7: Whitespace only"
printf "   \n  \t  " | python main.py
echo ""

echo "All integration tests completed!"

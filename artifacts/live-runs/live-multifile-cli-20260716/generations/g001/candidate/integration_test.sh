#!/bin/bash
# Integration test script for sentence analyzer

echo "Running integration tests..."
echo ""

# Test 1: Basic sentence
echo "Test 1: Basic sentence"
result=$(echo "The quick brown fox jumps" | python main.py)
echo "Input: 'The quick brown fox jumps'"
echo "Output: $result"
echo ""

# Test 2: Repeated words
echo "Test 2: Repeated words"
result=$(echo "hello world hello" | python main.py)
echo "Input: 'hello world hello'"
echo "Output: $result"
echo ""

# Test 3: Case insensitive
echo "Test 3: Case insensitive"
result=$(echo "Hello HELLO hello World" | python main.py)
echo "Input: 'Hello HELLO hello World'"
echo "Output: $result"
echo ""

# Test 4: Empty input
echo "Test 4: Empty input"
result=$(echo "" | python main.py)
echo "Input: ''"
echo "Output: $result"
echo ""

# Test 5: Single word
echo "Test 5: Single word"
result=$(echo "supercalifragilisticexpialidocious" | python main.py)
echo "Input: 'supercalifragilisticexpialidocious'"
echo "Output: $result"
echo ""

# Test 6: Punctuation
echo "Test 6: Punctuation"
result=$(echo "Hello, world! How are you?" | python main.py)
echo "Input: 'Hello, world! How are you?'"
echo "Output: $result"
echo ""

# Test 7: Multiple spaces
echo "Test 7: Multiple spaces"
result=$(echo "one    two     three" | python main.py)
echo "Input: 'one    two     three'"
echo "Output: $result"
echo ""

echo "All integration tests completed!"

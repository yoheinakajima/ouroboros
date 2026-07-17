#!/bin/bash

echo "Test 1: Basic sentence"
echo '{"sentence": "The quick brown fox jumps"}' | python agent.py

echo -e "\nTest 2: Repeated words"
echo '{"sentence": "hello world hello"}' | python agent.py

echo -e "\nTest 3: Case insensitive"
echo '{"sentence": "Hello HELLO hello"}' | python agent.py

echo -e "\nTest 4: Empty sentence"
echo '{"sentence": ""}' | python agent.py

echo -e "\nTest 5: Whitespace only"
echo '{"sentence": "   "}' | python agent.py

echo -e "\nTest 6: Single word"
echo '{"sentence": "supercalifragilisticexpialidocious"}' | python agent.py

echo -e "\nTest 7: Multiple spaces"
echo '{"sentence": "one  two   three"}' | python agent.py

echo -e "\nTest 8: With punctuation"
echo '{"sentence": "Hello, world!"}' | python agent.py

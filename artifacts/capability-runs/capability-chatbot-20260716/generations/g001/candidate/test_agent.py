import json
import subprocess
import sys
import unittest


class AgentTests(unittest.TestCase):
    def run_agent(self, text):
        process = subprocess.run(
            [sys.executable, "agent.py"], input=text, text=True,
            capture_output=True, check=False
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stderr, "")
        return [json.loads(line) for line in process.stdout.splitlines()]

    def test_rules_and_memory(self):
        output = self.run_agent(
            '{"message":"hello"}\n'
            '{"session":"a","message":"Who are you?"}\n'
            '{"session":"a","message":"My name is Ada."}\n'
            '{"session":"b","message":"What is my name?"}\n'
            '{"session":"a","message":"What is my name?"}\n'
            '{"message":"Tell me about oceans."}\n'
        )
        self.assertEqual(output, [
            {"session": "default", "reply": "Hello! How can I help you?"},
            {"session": "a", "reply": "I am a chatbot."},
            {"session": "a", "reply": "Nice to meet you, Ada!"},
            {"session": "b", "reply": "I don't know your name yet."},
            {"session": "a", "reply": "Your name is Ada."},
            {"session": "default", "reply": "You said: Tell me about oceans."},
        ])

    def test_invalid_requests_recover(self):
        output = self.run_agent('not-json\n[]\n{"message":2}\n{"session":3,"message":"hello"}\n{"message":"hello"}\n')
        self.assertEqual(output[:4], [{"error": "Invalid request"}] * 4)
        self.assertEqual(output[4], {"session": "default", "reply": "Hello! How can I help you?"})

    def test_blank_lines_do_not_emit(self):
        self.assertEqual(self.run_agent('\n  \n{"message":"hey"}\n'), [
            {"session": "default", "reply": "Hello! How can I help you?"}
        ])


if __name__ == "__main__":
    unittest.main()

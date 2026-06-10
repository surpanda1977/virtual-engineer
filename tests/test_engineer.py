"""Tests for the Virtual Engineer's mock brain.

Run with:
    python -m pytest        (if you install pytest)
or with the bundled unittest runner (from the project root):
    python -m unittest discover -s tests -t .
"""

import unittest
from unittest import mock

from app import config
from app.engineer import classify, generate_reply

# Unit tests must be deterministic and offline — force the mock path even when a
# real ANTHROPIC_API_KEY is configured in .env. (The live Claude path is verified
# separately.)
_patcher = None


def setUpModule():
    global _patcher
    _patcher = mock.patch.object(config, "use_real_llm", return_value=False)
    _patcher.start()


def tearDownModule():
    if _patcher:
        _patcher.stop()


class TestClassify(unittest.TestCase):
    def test_review_intent(self):
        self.assertEqual(classify("Can you review this function?"), "review")

    def test_debug_intent(self):
        self.assertEqual(classify("I got a KeyError exception"), "debug")

    def test_explain_intent(self):
        self.assertEqual(classify("Explain what a decorator is"), "explain")

    def test_generate_intent(self):
        self.assertEqual(classify("Write me a FastAPI endpoint"), "generate")

    def test_greeting_intent(self):
        self.assertEqual(classify("Hello there"), "greeting")

    def test_general_fallback(self):
        self.assertEqual(classify("foo bar baz"), "general")


class TestGenerateReply(unittest.TestCase):
    def test_returns_nonempty_text(self):
        reply = generate_reply("Hello")
        self.assertTrue(reply.text.strip())
        self.assertEqual(reply.intent, "greeting")

    def test_review_has_suggestions(self):
        reply = generate_reply("Please review my code")
        self.assertGreater(len(reply.suggestions), 0)

    def test_history_is_accepted(self):
        history = [{"role": "user", "content": "hi"}]
        reply = generate_reply("explain closures", history)
        self.assertEqual(reply.intent, "explain")


if __name__ == "__main__":
    unittest.main()

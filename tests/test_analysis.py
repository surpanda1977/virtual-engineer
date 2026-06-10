"""Tests for the document ingestion + analysis layers."""

import io
import unittest
from unittest import mock

from app import config
from app.analysis import analyze_documents
from app.ingest import ExtractedDoc, extract

# Force the deterministic offline/heuristic path even when a real
# ANTHROPIC_API_KEY is set, so unit tests never hit the network.
_patcher = None


def setUpModule():
    global _patcher
    _patcher = mock.patch.object(config, "use_real_llm", return_value=False)
    _patcher.start()


def tearDownModule():
    if _patcher:
        _patcher.stop()


def _csv_bytes() -> bytes:
    rows = [
        "Date,Type,Description",
        "2026-01-05,Bug,Login page crashes with a fatal error on submit",
        "2026-01-18,Request,Please add the ability to export reports to Excel",
        "2026-02-02,Bug,The dashboard is very slow and times out",
        "2026-02-20,Request,Would like an integration with our API",
        "2026-02-25,Incident,Service outage caused downtime for 2 hours",
    ]
    return ("\n".join(rows)).encode("utf-8")


class TestIngest(unittest.TestCase):
    def test_csv_extraction(self):
        doc = extract("tickets.csv", _csv_bytes())
        self.assertEqual(doc.filetype, "csv")
        self.assertEqual(doc.metadata["columns"], 3)
        self.assertIn("Login page crashes", doc.text)
        self.assertTrue(doc.tables)

    def test_text_extraction(self):
        doc = extract("notes.txt", b"This feature would be great. The app failed twice.")
        self.assertEqual(doc.filetype, "text")
        self.assertGreater(doc.word_count, 5)

    def test_unknown_falls_back_to_text(self):
        doc = extract("weird.xyz", b"hello world")
        self.assertEqual(doc.text.strip(), "hello world")

    def test_bad_pdf_does_not_crash(self):
        doc = extract("broken.pdf", b"not really a pdf")
        self.assertEqual(doc.filetype, "pdf")
        self.assertIsNotNone(doc.error)


class TestAnalysis(unittest.TestCase):
    def setUp(self):
        self.result = analyze_documents([extract("tickets.csv", _csv_bytes())])

    def test_detects_issues_and_requests(self):
        self.assertGreater(len(self.result.issues), 0)
        self.assertGreater(len(self.result.requests), 0)

    def test_categories_populated(self):
        self.assertTrue(self.result.issue_categories)
        self.assertTrue(self.result.request_categories)

    def test_builds_time_trend(self):
        # Two distinct months (2026-01, 2026-02) appear in the data.
        periods = {t.period for t in self.result.trends}
        self.assertIn("2026-01", periods)
        self.assertIn("2026-02", periods)

    def test_summary_is_nonempty(self):
        self.assertTrue(self.result.summary.strip())

    def test_top_terms(self):
        self.assertTrue(self.result.top_terms)

    def test_to_dict_is_serialisable(self):
        import json
        json.dumps(self.result.to_dict())  # must not raise

    def test_empty_batch_summary(self):
        res = analyze_documents([ExtractedDoc(filename="blank.txt", filetype="text", text="")])
        self.assertEqual(res.total_files, 1)
        self.assertIn("didn't detect", res.summary)


if __name__ == "__main__":
    unittest.main()

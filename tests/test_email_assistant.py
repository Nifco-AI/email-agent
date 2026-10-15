import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import email_assistant as app


class EmailAssistantTests(unittest.TestCase):
    def setUp(self):
        self.emails = json.loads((app.ROOT / "data/emails.json").read_text())
        self.batch = app.AnalysisBatch.model_validate_json(
            (app.ROOT / "data/mock_results.json").read_text())

    def test_mock_full_flow_without_environment_or_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            for name in ("emails.json", "mock_results.json"):
                (root / "data" / name).write_bytes((app.ROOT / "data" / name).read_bytes())
            with patch.object(app, "ROOT", root), patch("sys.argv", ["email_assistant", "--mock"]), \
                    patch("openai.OpenAI", side_effect=AssertionError("API forbidden")):
                self.assertEqual(app.main(), 0)
            report = json.loads((root / "outputs/mock/results.json").read_text())
            markdown = (root / "outputs/mock/results.md").read_text()
            self.assertEqual(report["mode"], "mock")
            self.assertEqual(len(report["emails"]), 5)
            self.assertEqual(len({item["category"] for item in report["emails"]}), 5)
            self.assertEqual(report["emails"][0]["job_match"], "未知")
            self.assertEqual([item["priority"] for item in report["emails"]],
                             ["medium", "high", "high", "low", "low"])
            self.assertEqual(report["emails"][2]["todos"][0]["deadline"], "未知")
            self.assertIn("2026-10-20 17:00 Singapore time", markdown)
            self.assertIn("优先级：high", markdown)
            for item in report["emails"][3:]:
                self.assertEqual(item["todos"], [])
                self.assertEqual(item["reply_needed"], "no")
            self.assertNotIn("print your API key", markdown)

    def test_api_contract_and_untrusted_data(self):
        with patch.object(app, "load_api_configuration", return_value=("dummy-test-key", "test-model")), \
                patch("openai.OpenAI") as constructor:
            client = constructor.return_value.__enter__.return_value
            client.responses.parse.return_value = SimpleNamespace(status="completed", output_parsed=self.batch)
            self.assertEqual(app.analyze_with_api(self.emails), self.batch)
            args = client.responses.parse.call_args.kwargs
            self.assertEqual(args["model"], "test-model")
            self.assertIs(args["text_format"], app.AnalysisBatch)
            self.assertFalse(args["store"])
            self.assertNotIn("tools", args)
            self.assertEqual(args["input"][0]["content"], app.INSTRUCTIONS)
            self.assertEqual(json.loads(args["input"][1]["content"])["emails"], self.emails)
            self.assertNotIn("dummy-test-key", args["input"][1]["content"])
            client.responses.parse.return_value = SimpleNamespace(status="completed", output_parsed=None)
            with self.assertRaises(ValueError):
                app.analyze_with_api(self.emails)

    def test_api_loads_local_dotenv(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text(
                "OPENAI_API_KEY=test-key-from-dotenv\nOPENAI_MODEL=test-model-from-dotenv\n")
            with patch.object(app, "ROOT", root), patch("openai.OpenAI") as constructor:
                client = constructor.return_value.__enter__.return_value
                client.responses.parse.return_value = SimpleNamespace(
                    status="completed", output_parsed=self.batch)
                app.analyze_with_api(self.emails)
            arguments = client.responses.parse.call_args.kwargs
            self.assertEqual(arguments["model"], "test-model-from-dotenv")
            self.assertEqual(constructor.call_args.kwargs["api_key"], "test-key-from-dotenv")
            self.assertEqual(constructor.call_args.kwargs["base_url"], "https://api.openai.com/v1")

    def test_incomplete_coverage_rejected(self):
        self.batch.emails.pop()
        with self.assertRaises(ValueError):
            app.validate_results(self.batch, self.emails)

    def test_priority_defaults_to_medium(self):
        payload = self.batch.emails[0].model_dump()
        payload.pop("priority")
        self.assertEqual(app.EmailAnalysis.model_validate(payload).priority, "medium")

    def test_priority_is_constrained(self):
        payload = self.batch.emails[0].model_dump()
        payload["priority"] = "urgent"
        with self.assertRaises(ValueError):
            app.EmailAnalysis.model_validate(payload)

    def test_markdown_escapes_active_content(self):
        text = app.markdown_text('<script>alert(1)</script> [click](https://example.com)')
        self.assertNotIn("<script>", text)
        self.assertIn("\\[click\\]", text)


if __name__ == "__main__":
    unittest.main()

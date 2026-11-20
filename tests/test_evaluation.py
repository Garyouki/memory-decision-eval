import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path

from memory_decision_eval import CASES, Decision, Prediction, ToolCall, evaluate
from memory_decision_eval.__main__ import main, read_predictions
from memory_decision_eval.benchmark import demo_predictions


class EvaluationTests(unittest.TestCase):
    def test_demo_scores_declared_and_actual_decisions_independently(self):
        result = evaluate(demo_predictions())
        self.assertEqual(result.total, 8)
        self.assertEqual(result.decisions_correct, 7)
        self.assertEqual(result.tool_calls_correct, 6)
        self.assertEqual(result.both_correct, 5)
        self.assertEqual(result.unexpected_writes, 1)
        scores = {case.case_id: case for case in result.cases}
        self.assertTrue(scores["outline/one-time"].decision_correct)
        self.assertFalse(scores["outline/one-time"].tool_calls_correct)
        self.assertFalse(scores["delivery/stale"].decision_correct)
        self.assertTrue(scores["delivery/stale"].tool_calls_correct)

    def test_wrong_target_and_extra_write_are_detected(self):
        predictions = list(demo_predictions())
        predictions[6] = Prediction(
            "release/stale",
            Decision.VERIFY,
            (
                ToolCall("verify_source", "atlas_handbook.release_channel"),
                ToolCall("write_memory", "atlas_handbook.release_channel"),
            ),
        )
        result = evaluate(predictions)
        scores = {case.case_id: case for case in result.cases}
        self.assertFalse(scores["release/ambiguous"].tool_calls_correct)
        self.assertFalse(scores["release/stale"].tool_calls_correct)
        self.assertTrue(scores["release/stale"].unexpected_write)
        self.assertEqual(result.unexpected_writes, 2)

    def test_requires_one_prediction_per_known_case(self):
        predictions = demo_predictions()
        for rows, message in (
            (predictions[:-1], "missing predictions"),
            (predictions + predictions[:1], "duplicate case ID"),
            (
                predictions + (Prediction("unknown", Decision.EPHEMERAL, ()),),
                "unknown case ID",
            ),
        ):
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(ValueError, message),
            ):
                evaluate(rows)
        self.assertEqual(evaluate(reversed(predictions)), evaluate(predictions))

    def test_case_export_includes_context_without_labels(self):
        with redirect_stdout(io.StringIO()) as output:
            main(["--cases"])
        rows = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(
            [row["case_id"] for row in rows], [case.case_id for case in CASES]
        )
        for row in rows:
            self.assertEqual(
                set(row), {"case_id", "original_interaction", "reuse_context", "target"}
            )

    def test_cli_scores_external_jsonl_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            path.write_text(
                "\n".join(json.dumps(asdict(row)) for row in demo_predictions()),
                encoding="utf-8",
            )
            with redirect_stdout(io.StringIO()) as output:
                main(["--predictions", str(path), "--json"])
            report = json.loads(output.getvalue())
            self.assertEqual(report["source"], "provided_traces")
            self.assertEqual(report["both_correct"], 5)
            self.assertEqual(len(report["cases"]), 8)

    def test_malformed_trace_reports_line_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "predictions.jsonl"
            path.write_text(
                '\n{"case_id":"outline/one-time","decision":"ephemeral","tool_calls":null}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError, "line 2: tool_calls must be an array"
            ):
                read_predictions(path)

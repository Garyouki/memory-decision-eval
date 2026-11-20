"""Expose the demo, case inputs, and JSONL trace scoring."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from . import CASES, Decision, Prediction, ToolCall, __version__, evaluate
from .benchmark import demo_predictions


def read_predictions(path: Path) -> list[Prediction]:
    predictions = []
    with path.open(encoding="utf-8-sig") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
                    raise TypeError(
                        "prediction must be an object with a string case_id"
                    )
                decision = Decision(row.get("decision"))
                calls = row.get("tool_calls")
                if not isinstance(calls, list):
                    raise TypeError("tool_calls must be an array, even when empty")
                tools = []
                for call in calls:
                    if (
                        not isinstance(call, dict)
                        or not isinstance(call.get("name"), str)
                        or not isinstance(call.get("target"), str)
                    ):
                        raise TypeError("each tool call needs a string name and target")
                    tools.append(ToolCall(call["name"], call["target"]))
                predictions.append(Prediction(row["case_id"], decision, tuple(tools)))
            except (TypeError, ValueError) as error:
                raise ValueError(f"line {number}: {error}") from error
    return predictions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="memory-decision-eval", description=__doc__)
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument(
        "--cases", action="store_true", help="Emit unlabeled case inputs as JSONL."
    )
    inputs.add_argument(
        "--predictions", type=Path, help="Score a JSONL file of observed traces."
    )
    parser.add_argument(
        "--json", action="store_true", help="Emit the full evaluation as JSON."
    )
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args(argv)

    if args.cases:
        for case in CASES:
            print(
                json.dumps(
                    {
                        "case_id": case.case_id,
                        "original_interaction": case.original_interaction,
                        "reuse_context": case.reuse_context,
                        "target": case.target,
                    }
                )
            )
        return

    try:
        external = args.predictions is not None
        predictions = (
            read_predictions(args.predictions) if external else demo_predictions()
        )
        result = evaluate(predictions)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    source = "provided_traces" if external else "fabricated_demo"
    if args.json:
        print(
            json.dumps(
                {"version": __version__, "source": source, **asdict(result)}, indent=2
            )
        )
        return

    print(f"Memory Decision Eval {__version__} | {source} | {result.total} cases")
    print(f"Declared decision correct: {result.decisions_correct}/{result.total}")
    print(f"Observed tool trace correct: {result.tool_calls_correct}/{result.total}")
    print(f"Both correct: {result.both_correct}/{result.total}")
    print(f"Cases with an unexpected durable write: {result.unexpected_writes}")


if __name__ == "__main__":
    main()

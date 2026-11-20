"""Paired synthetic memory cases and scoring for declared and observed actions."""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    PERSIST = "persist"
    EPHEMERAL = "ephemeral"
    VERIFY = "verify"
    CLARIFY = "clarify"


@dataclass(frozen=True)
class ToolCall:
    name: str
    target: str


@dataclass(frozen=True)
class Case:
    case_id: str
    original_interaction: str
    reuse_context: str
    target: str
    expected_decision: Decision
    expected_calls: tuple[ToolCall, ...]


@dataclass(frozen=True)
class Prediction:
    case_id: str
    decision: Decision
    tool_calls: tuple[ToolCall, ...]


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    expected_decision: Decision
    declared_decision: Decision
    expected_calls: tuple[ToolCall, ...]
    observed_calls: tuple[ToolCall, ...]
    decision_correct: bool
    tool_calls_correct: bool
    unexpected_write: bool


@dataclass(frozen=True)
class Evaluation:
    total: int
    decisions_correct: int
    tool_calls_correct: int
    both_correct: int
    unexpected_writes: int
    cases: tuple[CaseScore, ...]


CASES = (
    Case(
        "outline/standing",
        "Please use numbered headings for all my project outlines from now on.",
        "The user requests an outline for a new project.",
        "outline.heading_style",
        Decision.PERSIST,
        (ToolCall("write_memory", "outline.heading_style"),),
    ),
    Case(
        "outline/one-time",
        "Please use numbered headings just for this project outline.",
        "The user asks to add a section to that same outline.",
        "outline.heading_style",
        Decision.EPHEMERAL,
        (),
    ),
    Case(
        "draft/standing",
        "Please always include a date in the filenames of my meeting-note drafts.",
        "The user asks to save a draft from a new meeting.",
        "meeting_notes.filename_date",
        Decision.PERSIST,
        (ToolCall("write_memory", "meeting_notes.filename_date"),),
    ),
    Case(
        "draft/one-time",
        "Please include a date in the filename of this meeting-note draft only.",
        "The user asks to save the draft from that meeting after an edit.",
        "meeting_notes.filename_date",
        Decision.EPHEMERAL,
        (),
    ),
    Case(
        "delivery/stale",
        "Last week the office delivery for the Cedar event was scheduled for Thursday.",
        "The user asks for Cedar's current delivery window. The dispatch board can "
        "return a current record for Cedar.",
        "cedar.delivery_window",
        Decision.VERIFY,
        (ToolCall("verify_source", "cedar.delivery_window"),),
    ),
    Case(
        "delivery/ambiguous",
        "Last week Cedar and Birch each had a Thursday delivery.",
        "The user asks what time 'the delivery' is now. The dispatch board lists both "
        "events, and the conversation leaves the intended event ambiguous.",
        "delivery.event",
        Decision.CLARIFY,
        (ToolCall("ask_user", "delivery.event"),),
    ),
    Case(
        "release/stale",
        "At the last planning meeting, the Atlas handbook was in the preview channel.",
        "The user asks about the Atlas handbook's current release channel. A release "
        "registry provides its current entry.",
        "atlas_handbook.release_channel",
        Decision.VERIFY,
        (ToolCall("verify_source", "atlas_handbook.release_channel"),),
    ),
    Case(
        "release/ambiguous",
        "Both the Atlas handbook and the Atlas training deck were in preview.",
        "The user asks, 'Is Atlas still in preview?' Both items are listed separately "
        "and the user has given no hint about which to check.",
        "atlas.item",
        Decision.CLARIFY,
        (ToolCall("ask_user", "atlas.item"),),
    ),
)


def evaluate(predictions: Iterable[Prediction]) -> Evaluation:
    """Score one complete trace per built-in case, in fixture order."""
    known_ids = {case.case_id for case in CASES}
    by_id = {}
    for prediction in predictions:
        case_id = prediction.case_id
        if case_id not in known_ids:
            raise ValueError(f"unknown case ID: {case_id}")
        if case_id in by_id:
            raise ValueError(f"duplicate case ID: {case_id}")
        by_id[case_id] = prediction
    missing = sorted(known_ids - by_id.keys())
    if missing:
        raise ValueError(f"missing predictions for: {', '.join(missing)}")

    scores = []
    for case in CASES:
        prediction = by_id[case.case_id]
        scores.append(
            CaseScore(
                case_id=case.case_id,
                expected_decision=case.expected_decision,
                declared_decision=prediction.decision,
                expected_calls=case.expected_calls,
                observed_calls=prediction.tool_calls,
                decision_correct=prediction.decision == case.expected_decision,
                tool_calls_correct=prediction.tool_calls == case.expected_calls,
                unexpected_write=case.expected_decision != Decision.PERSIST
                and any(call.name == "write_memory" for call in prediction.tool_calls),
            )
        )
    return Evaluation(
        total=len(scores),
        decisions_correct=sum(row.decision_correct for row in scores),
        tool_calls_correct=sum(row.tool_calls_correct for row in scores),
        both_correct=sum(
            row.decision_correct and row.tool_calls_correct for row in scores
        ),
        unexpected_writes=sum(row.unexpected_write for row in scores),
        cases=tuple(scores),
    )


def demo_predictions() -> tuple[Prediction, ...]:
    """Use fabricated predictions that expose failures on either scoring channel."""
    overrides = {
        "outline/one-time": Prediction(
            "outline/one-time",
            Decision.EPHEMERAL,
            (ToolCall("write_memory", "outline.heading_style"),),
        ),
        "delivery/stale": Prediction(
            "delivery/stale",
            Decision.CLARIFY,
            (ToolCall("verify_source", "cedar.delivery_window"),),
        ),
        "release/ambiguous": Prediction(
            "release/ambiguous",
            Decision.CLARIFY,
            (ToolCall("ask_user", "atlas_handbook.release_channel"),),
        ),
    }
    return tuple(
        overrides.get(case.case_id)
        or Prediction(case.case_id, case.expected_decision, case.expected_calls)
        for case in CASES
    )

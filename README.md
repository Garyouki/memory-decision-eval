# Memory Decision Eval

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.24430281.svg)](https://doi.org/10.5281/zenodo.24430281)

A small offline evaluation inspired by the NORA paper *Remember, Verify, or
Ask?* It scores the decision an agent declares and the tool calls recorded by
its runner. The eight synthetic cases cover durable memory, one-time use,
verification of changing facts, and clarification of ambiguous intent.

## Run the demo

From a checkout with Python 3.10 or later, run `python -m memory_decision_eval`.
This uses fabricated predictions so you can inspect what happens when the
declared decision and the observed tool trace disagree. The example needs
neither model access nor an API key. Add `--json` for per-case results.

| Metric | Fabricated demo |
|---|---:|
| Declared decisions correct | 7 / 8 |
| Observed tool traces correct | 6 / 8 |
| Both correct | 5 / 8 |
| Cases with an unexpected durable write | 1 |

## Score your agent's traces

1. Export the case inputs with
   `python -m memory_decision_eval --cases > cases.jsonl`.
2. Pass `original_interaction` and `reuse_context` to your agent. Use the case
   ID for joining records. Keep benchmark IDs and reference labels outside the
   model input. Record the declared decision and normalize the memory-related
   calls from the runner's trace to the tool names below. Use the target
   namespace shown by the case export to normalize actual call targets.
3. Write one UTF-8 JSONL row per case. Run
   `python -m memory_decision_eval --predictions predictions.jsonl --json`.

A prediction row has a `case_id`, a `decision`, and an array named `tool_calls`.
Here is one complete row for a verification case.

```json
{"case_id":"delivery/stale","decision":"verify","tool_calls":[{"name":"verify_source","target":"cedar.delivery_window"}]}
```

| Declared decision | Reference trace |
|---|---|
| `persist` | One `write_memory` call for the intended memory key |
| `ephemeral` | An empty array of memory-related calls |
| `verify` | One `verify_source` call for the current fact |
| `clarify` | One `ask_user` call for the ambiguous intent or reference |

Tool scoring compares the observed sequence of names and targets with the
reference sequence. Wrong targets, missing calls, and extra memory-related
calls all affect the trace score. An unexpected durable write is a case
where the trace includes `write_memory` and the reference decision is
different from `persist`. Case IDs must be unique and all eight cases must
be present. Blank lines are allowed.

These fixtures are a smoke evaluation for scope and tool selection. The
counts apply to these eight cases. Storage, tool execution success, and
downstream task quality are outside the scoring contract. The original
paper's results use its own larger benchmark and evaluation conditions.

## Install and test

Install from the repository with `python -m pip install .`. The GitHub
release also provides a wheel. After installation, `memory-decision-eval`
is available as a shell command. Python integrations can import `CASES`,
`Prediction`, `ToolCall`, and `evaluate` from `memory_decision_eval`.

Run the tests with `python -m unittest discover -s tests -v`.

## Research provenance

The implementation and all eight cases were written for this repository.
The four decision types and the motivation for scoring declared decisions
and tool traces separately come from the NORA paper by Baichuan Li, Junyi
Yao, and Zihao Zheng. The dataset for this release consists of synthetic
examples authored for the smoke evaluation.

- [Remember, Verify, or Ask? (ACL Anthology)](https://aclanthology.org/2026.nora-1.2/)
- [Versioned preprint](https://arxiv.org/abs/2608.19564v2)
- [Software citation](CITATION.cff) and [MIT license](LICENSE)

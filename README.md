# compact-audit

An offline, deterministic Python CLI that compares a pre-compaction transcript
with the summary or handover note that replaced it. It extracts critical items
and reports which surfaces were kept or dropped, with category totals and
severity for triage. No LLM, network calls, keys, or runtime dependencies.
Python 3.9+; MIT licensed.

## Usage

Install the locally built wheel with `python3 -m pip install --no-index dist/compact_audit-0.1.0-py3-none-any.whl`.

```sh
compact-audit --version
compact-audit audit examples/sample-transcript.jsonl examples/sample-summary.md
compact-audit audit examples/sample-transcript.jsonl examples/sample-summary.md --json
compact-audit audit transcript.txt summary.md --min-severity medium
python3 -m compact_audit --help
```

The included examples are entirely synthetic. Their full-coverage summary
returns PASS (exit 0). Removing its migration decision makes the audit FAIL
(exit 2). JSON reports contain the same totals, dropped items, parse-error count,
truncation indicator, verdict, and limitation as human reports.

## Inputs and extraction

Transcripts are UTF-8 JSONL (`.jsonl`, case insensitive) or plain text (`.txt` or
`.md`). Plain text is split into non-empty lines. JSONL requires one object per
non-empty line; fields use `content`, then `text`, then `message` when the earlier
field is absent. Other fields are ignored. Missing text fields yield no items;
non-string selected fields, non-objects, and malformed JSON count as parse
errors. Multiline strings are split into source lines. Blank lines are ignored.
The summary is a UTF-8 text or Markdown file. Empty transcripts yield zero items;
empty summaries drop every extracted item.

These short, case-insensitive pattern lists are heuristic:

| Category | Triggers | Severity if dropped |
| --- | --- | --- |
| decision | `Decision:`, `decided to`, `we will use`, `chosen`, `agreed to`, `going with` | HIGH |
| constraint | `must not`, `never `, `do not`, `must always`, `only ` followed by a non-empty clause, `required` | HIGH |
| error | word `Error`, `Traceback`, `FAILED`, `failed with`, or `exit code` followed by a non-zero integer | HIGH |
| file_edit | `edited`, `changed`, `created`, `deleted`, `modified`, `wrote`, `rewrote`, `updated` plus a recognized path | MEDIUM |
| todo | `TODO`, `FIXME`, `not done`, `remaining`, `next step`, `still need` | MEDIUM |

Recognized file paths end in `.py`, `.js`, `.ts`, `.md`, `.json`, `.yaml`,
`.toml`, `.go`, or `.rs`, or are under `src/`, `tests/`, or `docs/`.
Each matched path becomes a separate item. A line can produce several categories.
Items deduplicate by category and normalized key. The first 500 unique items in
transcript order are retained; additional unique items set `truncated` to true.
Within a line, category order is decision, constraint, error, file_edit, todo.
Source text is truncated to 500 characters; matching keys retain the full line.

Matching lowercases text and collapses punctuation, underscores, and whitespace
to single spaces. Whole normalized line keys must occur as substrings of the
normalized summary. Error keys strip digits; the summary also strips digits for
error matching. File edits match either their normalized full path or basename.

## Exit codes

| Code | Verdict | Meaning |
| --- | --- | --- |
| 0 | PASS | No dropped items |
| 1 | WARN | Dropped items exist, but none reach the selected threshold |
| 2 | FAIL | A dropped item reaches the threshold, or any parse error occurred |

The default threshold is `high`: MEDIUM-only drops warn with exit 1. With
`--min-severity medium`, any drop fails with exit 2. Thus an audit with no
threshold-level drops can still warn; PASS is reserved for no drops. Input I/O,
encoding, and CLI usage errors also return 2 with an explanatory diagnostic.

## Honest limitations

This is surface matching, not semantic judgement. Paraphrase is not detected
and causes false DROPPED results. DROPPED means **not found by surface matching —
verify manually**, rather than certainty that meaning was lost. Severity and
thresholds are triage signals, not evidence that a summary is safe or complete.

Heuristic patterns can miss implicit decisions or overmatch incidental language
(such as unrestricted uses of “only”). Basename matches may conflate different
files; substring matches can accept negated statements. Digit stripping can
conflate distinct errors. A PASS covers only extracted surfaces, and truncation
leaves later items unaudited. Review truncation and the original context manually.
The tool does not inspect repositories, execute transcript content, validate
claims, or recover missing context.

## Differentiation

- **Succession** is a Claude-Code-only plugin with git-pointer claim checks;
  compact-audit is an offline cross-harness CLI over transcript and summary text.
- **session-handover** generates a handover pack; compact-audit audits any summary,
  including auto-compaction output, for loss.
- **catnap** prevents mid-task compaction; compact-audit measures surface items a
  completed compaction left out.
- **model-canary** probes model drift; compact-audit audits context loss.

## Development

Runtime and tests use only the Python standard library. Packaging uses setuptools
and wheel through `pyproject.toml`, with the standard `build` frontend.

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
python3 -m build
```

For an offline environment with build, setuptools, and wheel already installed,
use `python3 -m build --no-isolation` to avoid dependency downloads. Build outputs
are artifacts under `dist/`, not source files.

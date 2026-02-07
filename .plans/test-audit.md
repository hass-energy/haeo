# Test Audit Plan (HAEO)

## Purpose

Create a comprehensive audit of all pytest-collected tests (excluding scenarios) with one audit file per test. Each audit file must contain frontmatter checkboxes for tracking review/decisions and a concise description of the behavior being tested.

## Scope

- Include: All tests collected by pytest under tests/.
- Exclude: Scenario tests (marked with `scenario`).
- Include fixture review: tests/conftest.py and any module-level conftest.

## Collection Command

Use pytest collection to enumerate tests:

- Command: `uv run pytest --collect-only -m "not scenario"`
- Output saved to: `.plans/pytest-collect.txt`
- Nodeid list saved to: `.plans/pytest-collect-nodeids.txt`
- Only lines starting with `tests/` are treated as nodeids

## Output Structure

Create `test_audit/` mirroring tests/:

- Example: tests/model/test_elements.py -> test_audit/model/test_elements/
- One audit file per test function or test method.
- Parameterized tests: one audit file per function/method with per-parameter entries in frontmatter.

## Audit Template (frontmatter-first)

Each audit file must begin with YAML frontmatter containing checkboxes:

- `status.reviewed` (bool)
- `status.decision` (string: undecided|keep|remove|combine)
- `status.behavior_documented` (bool)
- `status.redundancy_noted` (bool)
- `parameterized.per_parameter_review` (bool)
- `parameterized.cases[]` (list of parameter entries with per-case checkboxes)

Follow frontmatter with sections:

- Behavior summary
- Redundancy / overlap notes
- Decision rationale
- Fixtures used (if applicable)
- Next actions (if any)

## Subagent Workflow

Use subagents to review tests by folder to preserve context and speed up analysis:

- Assign one folder per subagent (e.g., tests/data, tests/elements, tests/model, tests/flows, tests/util, top-level tests).
- Each subagent returns a structured list: nodeid, behavior summary, redundancy notes, keep/remove/combine decision, and per-parameter notes.
- Apply updates to audit files from subagent output before moving to the next folder.

## Parameterized Test Handling

- If all parameters validate the same behavior, audit once with `per_parameter_review: false`.
- If parameters represent distinct behaviors (e.g., different element types), list each parameter under `parameterized.cases` and decide per case.

## Fixture Audit

Create a dedicated audit file for:

- tests/conftest.py
- any module conftest (e.g., tests/model/conftest.py)

Document:

- Purpose of each fixture
- Scope and usage
- Whether fixture is redundant or overly broad

## Execution Checklist

1. Run pytest collection, save output.
2. Create test_audit/ and template file.
3. Generate audit files from collection output.
4. Review tests file-by-file and fill in audit details.
5. Review fixtures and update fixture audit files.
6. Summarize findings and recommendations.

## Progress Tracking

Maintain progress by updating frontmatter checkboxes in each audit file. Use scripts to report completion based on these fields.

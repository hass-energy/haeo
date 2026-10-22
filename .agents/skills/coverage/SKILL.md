---
name: coverage
description: Analyze test coverage for the current branch and add tests for uncovered lines, using the remove-first decision tree before writing new tests. Use when asked about coverage, when codecov reports a drop on changed lines or a failing patch target, or when deciding what tests a change still needs.
---

# Code coverage analysis

Check coverage for the current branch and decide what each uncovered line needs: deletion, a stricter type, or a test.

## Step 1: run coverage

Run the unit test gate with coverage, as CI does:

```bash
uv run check test -- --cov=custom_components/haeo --cov-branch --cov-report=term-missing
```

Add `--cov-report=html` and open `htmlcov/index.html` for a line-by-line view.

To run only the tests a branch changed, list them against `origin/main`, since a local `main` may be stale.
Tests are colocated, so match every `tests/` directory, not just the top-level one:

```bash
git fetch origin main
git diff origin/main...HEAD --name-only -z --diff-filter=AM -- '**/tests/**/test_*.py' | \
    xargs -0 uv run pytest --cov=custom_components/haeo --cov-branch --cov-report=term-missing
```

## Step 2: what codecov enforces

[`codecov.yml`](../../../codecov.yml) sets the targets:

- **Patch**: at least 90% of the lines a pull request changes must be covered.
- **Project**: overall coverage may not drop by more than 1%.

Codecov can also report lines outside the diff whose coverage changed indirectly, such as a branch that a refactor made unreachable.

## Step 3: decide what each uncovered line needs

Work through the decision tree in the `testing` skill, in order: remove the code, tighten the types, add a parametrized case, combine tests, and only then write a bespoke test.
If no input can reach a line, the line is unreachable: delete it rather than testing it.

## Step 4: where cases go

Add a case to an existing data module before writing a new test function:

- **Model elements**: `VALID_CASES` in `core/model/tests/test_data/{model_element}.py`
- **Element adapters**: `CREATE_CASES` and `OUTPUTS_CASES` in `core/adapters/elements/tests/test_data/{element_type}.py`
- **Element flows**: `VALID_DATA` and `INVALID_DATA` in `flows/tests/test_data/{element_type}.py`
- **Everything else**: the `tests/` directory beside the module

The `testing` skill describes each of these structures.

## Step 5: verify and summarize

Re-run the coverage command, then `uv run check`.
Report the coverage of the changed files, the cases added, and any code removed as unreachable.

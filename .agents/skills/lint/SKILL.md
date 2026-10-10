---
name: lint
description: Run every CI gate locally — ruff lint and format, pyright, import boundaries, mdformat, prettier, version consistency, unit tests, scenario tests, frontend card checks, docs build — and fix whatever fails. Use before committing, before opening a pull request, when asked to lint, format, type check, verify, or make CI pass, and when diagnosing a red CI run.
---

# Lint, format, and type check

`tools/check.py` defines every gate once.
`.github/workflows/ci.yml` invokes it rather than repeating the commands, so a gate cannot pass locally and fail in CI because the two drifted apart.
Do not run the underlying tools individually; run the gate.

## Step 1: run the gates

```bash
uv run check          # every gate that runs locally, ~70s
uv run check --fast   # ruff, pyright and unit tests, ~35s
uv run check --list   # gate names and what each covers
```

One line per gate with timing, output only for failures, non-zero exit if anything failed.

Some gates cannot run outside GitHub Actions and are reported as skipped with the reason rather than silently omitted:

- `hassfest` and `hacs` are provided wholly by third-party actions.
- `guide` is slow and needs Playwright Firefox. It runs in `guides.yml` and is not part of the required check. Run it explicitly with `uv run check guide` when touching `docs/walkthroughs/`.

## Step 2: fix what failed

Apply the mechanical fixes first:

```bash
uv run check --fix
```

This runs the autofix form of every formatter gate, then re-checks.
Everything still failing needs a real change:

- **Ruff lint**: restructure the code so the rule is satisfied naturally.
    `# noqa` is a last resort and must carry a parenthesized reason.
    See the `python` skill.
- **Pyright**: strict mode. `typing.cast` is a banned API — fix the types or use a `TypeGuard`.
    A `# type: ignore` needs a written explanation of why nothing else worked.
- **Import boundaries**: `custom_components/haeo/core/**` may import only `highspy`, `numpy`, and `typing_extensions`.
    A broken contract means the import belongs on the Home Assistant side of the boundary.
- **Tests**: `filterwarnings = ["error"]`, so a new warning is a hard failure, and `timeout = 5` turns a hang into a timeout.
- **Scenario tests**: a diff means optimizer behavior changed.
    Confirm that is intended before regenerating with `--snapshot-update`.
- **Version consistency**: `pyproject.toml` and `custom_components/haeo/manifest.json` versions must match, and `homeassistant>=X` in `pyproject.toml` must equal `homeassistant` in `hacs.json`.
    Run `uv sync` after changing either.

The main branch is always clean, so any failure belongs to the current branch and must be fixed rather than worked around.

## Running a single gate

```bash
uv run check pyright
uv run check test -- -k battery      # arguments after -- go to the gate command
```

Pass-through arguments require exactly one gate.

## Changing what CI checks

Gates live in `GATES` in `tools/check.py`. To add one:

1. Add a `Gate` to `GATES` with its check command, and its autofix command if it has one.
2. Add a job to `.github/workflows/ci.yml` that runs `python3 tools/check.py <name>`, and add that job to the `ci-passed` needs list.

`tests/test_check_gates.py` fails if a gate exists without a CI job, if CI invokes a gate the runner does not define, or if a gate job is missing from the required check.
That test is why the two stay in step, so do not weaken it to make a change pass.

CI invokes the script as `python3 tools/check.py` rather than `uv run check`, because the Prettier and frontend jobs set up only Node.
The module is standard library only, so it runs without the project environment; the gate commands themselves still call `uv run ...` where needed.

On pull requests, reviewdog additionally annotates the diff for ruff, pyright, prettier and mdformat.
Those steps are advisory — `continue-on-error` — because the shared gate decides pass or fail.

Coverage is not a gate; codecov enforces it on changed lines. Use `/coverage` for that workflow.

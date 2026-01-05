---
description: Run linting, type checking, and formatting checks, then fix any issues found
---

# Lint, Format, and Type Check

Run all code quality checks and fix any issues found.

## Step 1: Run All Checks

Execute the following commands to check code quality:

### Python Linting

```bash
uv run ruff check
```

### Python Formatting

```bash
uv run ruff format --check
```

### Type Checking

```bash
uv run pyright
```

### Markdown Formatting

```bash
git ls-files -z '*.md' '*.mdx' | xargs -0 uv run mdformat --check
```

### JSON Formatting

```bash
npm ci
npx --yes prettier@3 --check .
```

## Step 2: Fix Issues

For each tool that reports issues:

### Ruff Linting Issues

- Run `uv run ruff check --fix` to auto-fix issues where possible
- Manually fix remaining issues according to Ruff's suggestions
- Follow HAEO coding standards from `.github/instructions/python.instructions.md`

### Ruff Formatting Issues

- Run `uv run ruff format` to automatically format Python code
- This will fix all formatting issues according to the project's style

### Pyright Type Errors

- Fix type errors by adding proper type hints
- Use `str | None` syntax, not `Optional[str]`
- Ensure all functions, methods, and variables have type hints
- See `.github/instructions/python.instructions.md` for typing guidelines

### Markdown Formatting Issues

- Run `git ls-files -z '*.md' '*.mdx' | xargs -0 uv run mdformat` to format markdown files
- Ensure semantic line breaks (one sentence per line)
- Follow documentation guidelines from `docs/developer-guide/documentation-guidelines.md`

### JSON Formatting Issues

- Run `npx --yes prettier@3 --write .` to format JSON files
- This will fix all JSON formatting issues

## Step 3: Verify All Checks Pass

After fixing issues, re-run all checks to ensure everything passes:

```bash
# Python checks
uv run ruff check
uv run ruff format --check
uv run pyright

# Markdown check
git ls-files -z '*.md' '*.mdx' | xargs -0 uv run mdformat --check

# JSON check
npx --yes prettier@3 --check .
```

## Step 4: Summary

Provide a summary of:

- Which checks initially failed
- What issues were fixed
- Any remaining issues that need manual attention
- Confirmation that all checks now pass

## Notes

- **Ruff** handles both linting and formatting for Python code
- **Pyright** provides strict type checking (typeCheckingMode = "strict")
- **mdformat** ensures markdown follows semantic line breaks
- **Prettier** formats JSON files consistently
- All fixes should maintain code functionality while improving quality
- When in doubt, follow existing code patterns in the codebase

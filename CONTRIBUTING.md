# Contribution guidelines

Contributing to this project should be as easy and transparent as possible.
We welcome contributions in many forms, whether it's:

- Reporting a bug
- Discussing the current state of the code
- Submitting a fix
- Proposing new features

## Github is used for everything

Github is used to host code, to track issues and feature requests, as well as accept pull requests.

Pull requests are the best way to propose changes to the codebase.

1. Fork the repo and create your branch from `main`.
2. If you've changed something, update the documentation.
3. Make sure your code lints and passes tests.
4. Issue that pull request!

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager

### Quick Start

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/haeo.git
cd haeo

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linters
uv run ruff check custom_components/ tests/
uv run ruff format custom_components/ tests/

# Type checking
uv run mypy custom_components/
```

See the [Developer Guide](https://ha-energy-optimiser.github.io/haeo/developer-guide/) for detailed setup instructions.

## Any contributions you make will be under the MIT Software License

In short, when you submit code changes, your submissions are understood to be under the same [MIT License](http://choosealicense.com/licenses/mit/) that covers the project.
Feel free to contact the maintainers if that's a concern.

## Report bugs using Github's [issues](../../issues)

GitHub issues are used to track public bugs.
Report a bug by [opening a new issue](../../issues/new/choose); it's that easy!

## Write bug reports with detail, background, and sample code

**Great Bug Reports** tend to have:

- A quick summary and/or background
- Steps to reproduce
    - Be specific!
    - Give sample code if you can.
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

People _love_ thorough bug reports. I'm not even kidding.

## Use a Consistent Coding Style

### Python Code

Use [ruff](https://github.com/astral-sh/ruff) to make sure the code follows the style:

```bash
# Check code style
uv run ruff check custom_components/ tests/

# Auto-format code
uv run ruff format custom_components/ tests/
```

### JavaScript, JSON, and YAML

Use [Prettier](https://prettier.io/) for JavaScript, JSON, and YAML files:

```bash
# Check formatting
npx prettier@3 --check .

# Auto-format
npx prettier@3 --write .
```

### Markdown

Use [mdformat](https://mdformat.readthedocs.io/) with [mdformat-mkdocs](https://github.com/KyleKing/mdformat-mkdocs) for markdown files:

```bash
# Check markdown formatting
uv run mdformat --check .

# Auto-format markdown
uv run mdformat docs/ .
```

Configuration is in `[tool.mdformat]` section of `pyproject.toml`.

**Why mdformat-mkdocs?** It understands MkDocs-specific syntax like admonitions (`!!! info`), tabs, and other Material theme features.
Standard markdown formatters would break these features.

## Test your code modification

Run the test suite before submitting:

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=custom_components.haeo --cov-report=html

# Run specific test file
uv run pytest tests/test_model.py

# Run scenario tests (skipped by default)
uv run pytest tests/scenarios/test_scenarios.py -m scenario
```

All tests must pass before your PR can be merged.
Note: Scenario tests are skipped by default and only run when explicitly requested with `-m scenario`.

## Documentation

If you've added or changed functionality, update the documentation:

```bash
# Build documentation locally
uv run mkdocs serve

# View at http://127.0.0.1:8000
```

Documentation is automatically deployed when changes are merged to `main`.

See the [Contributing Guide](https://ha-energy-optimiser.github.io/haeo/developer-guide/contributing/) in the documentation for more details.

## License

By contributing, you agree that your contributions will be licensed under its MIT License.

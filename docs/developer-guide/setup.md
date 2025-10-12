# Development Setup

Set up your development environment for HAEO.

## Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) package manager
- Git

## Installation

### Clone Repository

```bash
git clone https://github.com/ha-energy-optimiser/haeo.git
cd haeo
```

### Install Dependencies

```bash
uv sync
```

This installs all development dependencies including:

- pytest (testing)
- ruff (linting/formatting)
- mypy (type checking)
- mkdocs (documentation)

## Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_model.py

# With coverage
uv run pytest --cov=custom_components.haeo
```

## Code Quality

### Linting

```bash
uv run ruff check custom_components/ tests/
```

### Formatting

```bash
uv run ruff format custom_components/ tests/
```

### Type Checking

```bash
uv run mypy custom_components/
```

## Documentation

### Build Locally

```bash
uv run mkdocs serve
```

Visit http://127.0.0.1:8000

### Deploy

Documentation automatically deploys via GitHub Actions on push to main.

## Next Steps

- Read [Contributing](contributing.md) guidelines
- Explore [Architecture](architecture.md)
- Check [Testing](testing.md) guide

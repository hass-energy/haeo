# Development Setup

Set up your development environment for HAEO.

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- Git

## Installation

### Clone repository

```bash
git clone https://github.com/hass-energy/haeo.git
cd haeo
```

### Install dependencies

```bash
uv sync
```

This installs all development dependencies including:

- pytest (testing)
- ruff (linting/formatting)
- pyright (type checking)
- zensical (documentation)

## Local Home Assistant simulation

For interactive development with realistic input data and a browsable frontend:

```bash
uv run sim scenario1
```

See the [local simulation guide](local-sim.md) for options including accelerated time, ephemeral mode, and skipping automatic HAEO setup.

## Running tests

```bash
# Unit tests, as the test gate runs them
uv run check test

# Everything, including scenario, guide, and benchmark tests
uv run pytest

# Model element tests
uv run pytest custom_components/haeo/core/model/tests/

# With coverage
uv run pytest --cov=custom_components.haeo
```

## Code quality

### Linting

```bash
uv run ruff check
```

### Formatting

```bash
uv run ruff format
```

### Type checking

```bash
uv run pyright
```

## Documentation

### Build locally

```bash
uv run zensical serve
```

Visit http://127.0.0.1:8000

`uv run zensical build` is the documentation gate in `uv run check`.
It runs in strict mode, so a broken internal link or anchor fails it.

### Deploy

Documentation automatically deploys via GitHub Actions on push to main.

## Next steps

- Read [Contributing](contributing.md) guidelines
- Explore [Architecture](architecture.md)
- Check [Testing](testing.md) guide

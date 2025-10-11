# Contributing to HAEO

Thank you for your interest in contributing!

## Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linters and tests
6. Submit a pull request

## Code Standards

- **Python 3.13+** required
- **Type hints** on all functions
- **Docstrings** (Google style)
- **Tests** for new features
- **Ruff** formatting

## Testing

```bash
uv run pytest
uv run ruff check custom_components/ tests/
uv run mypy custom_components/
```

All checks must pass before merging.

## Documentation

Update documentation for:
- New features
- Configuration changes
- API modifications

Build docs locally:

```bash
uv run mkdocs serve
```

## Pull Request Process

1. Update CHANGELOG.md
2. Ensure all tests pass
3. Update documentation
4. Request review

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for details.

# Developer Guide

Welcome to the HAEO developer documentation!
This section covers architecture, development setup, and contribution guidelines.

## Quick Start

```bash
git clone https://github.com/ha-energy-optimiser/haeo.git
cd haeo
uv sync
uv run pytest
```

## Topics

- [Architecture](architecture.md) - System design overview
- [Setup](setup.md) - Development environment with `uv`
- [Units & Stability](units.md) - Unit system and numerical considerations
- [Energy Models](energy-models.md) - Creating new entity types
- [Coordinator](coordinator.md) - Data update coordinator pattern
- [Testing](testing.md) - Running and writing tests
- [Contributing](contributing.md) - Contribution workflow

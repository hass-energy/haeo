# Developer Guide

Welcome to the HAEO developer documentation!
This section covers architecture, development setup, and contribution guidelines.

## Quick Start

```bash
git clone https://github.com/hass-energy/haeo.git
cd haeo
uv sync
uv run pytest
```

## Architecture

HAEO uses a layered architecture separating user configuration from optimization modeling:

- [Architecture](architecture.md) - System design overview
- [Adapter Layer](adapter-layer.md) - Device Layer to Model Layer transformation

## Component Guides

- [Horizon Manager](horizon-manager.md) - Synchronized forecast time windows
- [Input Entities](inputs.md) - Intermediate input entity layer
- [Data Loading](data-loading.md) - Sensor data extraction and loading
- [Coordinator](coordinator.md) - Event-driven optimization coordinator
- [Config Flow](config-flow.md) - Configuration UI patterns
- [Energy Models](energy-models.md) - Creating new element types

## Development

- [Setup](setup.md) - Development environment with `uv`
- [Units & Stability](units.md) - Unit system and numerical considerations
- [Testing](testing.md) - Running and writing tests
- [Contributing](contributing.md) - Contribution workflow
- [Documentation Guidelines](documentation-guidelines.md) - Writing and maintaining docs

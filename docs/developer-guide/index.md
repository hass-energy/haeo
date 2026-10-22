# Developer guide

Welcome to the HAEO developer documentation!
This section covers architecture, development setup, and contribution guidelines.

## Quick start

```bash
git clone https://github.com/hass-energy/haeo.git
cd haeo
uv sync
uv run check
```

## Architecture

HAEO uses a layered architecture separating user configuration from optimization modeling:

- [Architecture](architecture.md) - Packages and how they fit together
- [Adapter layer](adapter-layer.md) - Device layer to model layer transformation
- [Energy models](energy-models.md) - Model elements, segments, and the network
- [Policy compilation](policy-compilation.md) - How power policies compile into the LP
- [VLAN optimization](vlan-optimization.md) - Keeping policy tags from multiplying variables

## Component guides

- [Horizon manager](horizon-manager.md) - Synchronized forecast time windows
- [Input entities](inputs.md) - Input stores and the entities that expose them
- [Data loading](data-loading.md) - Sensor data extraction and loading
- [Coordinator](coordinator.md) - Event-driven optimization coordinator
- [Config flow](config-flow.md) - Configuration UI patterns

## Development

- [Setup](setup.md) - Development environment with `uv`
- [Local simulation](local-sim.md) - A browsable Home Assistant running on scenario data
- [Typing philosophy](typing.md) - Type patterns and where checks belong
- [Units and stability](units.md) - Unit system and numerical considerations
- [Testing](testing.md) - Running and writing tests
- [Contributing](contributing.md) - Contribution workflow
- [Documentation guidelines](documentation-guidelines.md) - Writing and maintaining docs

# GitHub Copilot Instructions

This repository contains **HAEO** (Home Assistant Energy Optimizer) - a Python 3.13+ Home Assistant custom component for energy network optimization using linear programming.

## Project overview

HAEO optimizes energy usage across battery storage, grid import/export, loads, and generators using linear programming.
The integration provides real-time optimization based on energy prices, forecasts, and system constraints.

### Core components

- **Network**: Container managing elements and connections, runs optimization
- **Elements**: Battery, Grid, Load, Photovoltaics, Node - each with power/energy variables
- **Connections**: Define power flow constraints between elements
- **Model**: Linear programming formulation with constraints and cost functions
- **Coordinator**: Bridges HA entities with optimization network
- **Sensors**: Expose optimization results to Home Assistant

### Project structure

```
custom_components/haeo/     # Home Assistant integration
├── model/                  # LP model (constraints, variables, optimization)
├── elements/               # Energy elements (battery, grid, load, node, pv)
├── flows/                  # Config flow steps
├── sensors/                # Sensor implementations
└── translations/           # i18n strings
tests/                      # Test suite
├── scenarios/              # End-to-end scenario tests
docs/                       # Documentation
```

## Development tools

- **Package manager**: uv (use `uv sync` for dependencies, `uv run` to execute tools)
- **Testing**: pytest (scenarios use `-m scenario` marker)
- **Linting/Formatting**: Ruff
- **Type checking**: Pyright

## Agent behavioral rules

These rules apply to all AI agent interactions with this codebase:

### Clean changes

When making changes, don't leave behind comments describing what was once there.
Comments should always describe code as it exists without reference to former code.

### API evolution

When making changes, don't leave behind backwards-compatible interfaces for internal APIs.
There should always be a complete clean changeover.

### Error context

The main branch is always clean with no errors or warnings.
Any errors, warnings, or test failures you encounter are directly related to recent changes in the current branch/PR.
These issues must be fixed as part of the work - they indicate problems introduced by the changes being made.

### Property access

Always assume that accessed properties/fields which should exist do exist directly.
Rely on errors occurring if they do not when they indicate a coding error and not a possibly None value.
This is especially true in tests where you have added entities and then must access them later.
Having None checks there reduces readability and makes the test more fragile to passing unexpectedly.

## Universal code standards

- **Python**: 3.13+ with modern features (pattern matching, `str | None` syntax, f-strings, dataclasses)
- **Type hints**: Required on all functions, methods, and variables
- **Formatting**: Ruff
- **Linting**: Ruff
- **Type checking**: Pyright
- **Language**: American English for all code, comments, and documentation
- **Testing**: pytest with >95% coverage target

### SI units internally

Use SI units throughout all calculations and internal data structures:

- Power: Watts (W)
- Energy: Watt-hours (Wh)
- Time: seconds

Only convert to user-friendly units (kW, kWh, hours) when displaying to users or accepting user input.

### Translation and naming conventions

HAEO follows Home Assistant's entity naming conventions for sensor translations.
See `.github/instructions/translations.instructions.md` for detailed rules.

Key patterns for sensor display names using sentence case (capital first letter, rest lowercase):

1. **Power sensors**: Action + noun pattern ("Import power", "Charge power")
2. **Price sensors**: Qualifier + price pattern ("Import price", "Export price")
3. **Shadow price sensors**: Constraint + "shadow price" suffix ("Max import power shadow price")
4. **Connection sensors**: Use parameterized translations with `{source}` and `{target}` placeholders

Avoid special characters in translation display names as they are used in entity ID generation.

## Path-specific instructions

This repository uses path-specific instruction files in `.github/instructions/` that apply additional context based on the files being edited.
See that directory for domain-specific guidelines.

## Documentation

- [Documentation guidelines](../docs/developer-guide/documentation-guidelines.md) - Writing and maintaining docs
- [Units guide](../docs/developer-guide/units.md) - Unit conversion and conventions
- [Testing guide](../docs/developer-guide/testing.md) - Test patterns and scenarios

## Self-maintenance

When the user provides feedback about systemic corrections (coding patterns, style issues, architectural decisions, or recurring mistakes), update the appropriate instruction file to capture that feedback for future sessions.

See `.github/instructions/meta.instructions.md` for guidance on maintaining both Copilot instructions and Cursor rules in sync.

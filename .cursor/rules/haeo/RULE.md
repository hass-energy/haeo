---
description: HAEO project context and agent behavioral rules - always applied
alwaysApply: true
---

# HAEO Project Rules

This repository contains **HAEO** (Home Assistant Energy Optimizer) - a Python 3.13+ Home Assistant custom component for energy network optimization using linear programming.

## Core components

- **Network**: Container managing elements and connections, runs optimization
- **Elements**: Battery, Grid, Load, Photovoltaics, Node - each with power/energy variables
- **Connections**: Define power flow constraints between elements
- **Model**: Linear programming formulation with constraints and cost functions
- **Coordinator**: Bridges HA entities with optimization network
- **Sensors**: Expose optimization results to Home Assistant

## Project structure

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

## Self-maintenance

When the user provides feedback about systemic corrections (coding patterns, style issues, architectural decisions, or recurring mistakes), update the appropriate rule file to capture that feedback for future sessions.

See `.cursor/rules/meta/RULE.md` for guidance on maintaining both Cursor rules and Copilot instructions in sync.

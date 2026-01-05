---
description: HAEO project context and agent behavioral rules - always applied
alwaysApply: true
---

# GitHub Copilot Instructions

This repository contains **HAEO** (Home Assistant Energy Optimizer) - a Python 3.13+ Home Assistant custom component for energy network optimization using linear programming.

## Project overview

HAEO optimizes energy usage across battery storage, grid import/export, loads, and generators using linear programming.
The integration provides real-time optimization based on energy prices, forecasts, and system constraints.

### Core components

The integration follows a layered architecture:

- **Model layer** (`model/`): LP formulation with elements, constraints, and cost functions
- **Elements layer** (`elements/`): Bridges HA configuration with model layer via adapters
- **Coordinator** (`coordinator.py`): Orchestrates data loading, optimization, and result extraction
- **Sensors** (`sensors/`): Expose optimization results to Home Assistant
- **Config flows** (`flows/`): Subentry-based configuration for hub and elements

See [architecture guide](../docs/developer-guide/architecture.md) for detailed component interactions.

### Project structure

```
custom_components/haeo/     # Home Assistant integration
├── model/                  # LP model (constraints, variables, optimization)
├── elements/               # Element adapters (one subfolder per element type)
├── schema/                 # Shared utilities (UnitSpec, matches_unit_spec)
├── flows/                  # Hub and options config flows
├── sensors/                # Sensor implementations
├── data/                   # Data loading utilities
└── translations/           # i18n strings (en.json)
tests/                      # Test suite
├── flows/                  # Config flow tests with shared test_data/
├── elements/               # Element-specific tests (adapter, flow, model)
├── model/                  # Model layer tests
└── scenarios/              # End-to-end scenario tests
docs/                       # Documentation
```

## Development tools

- **Package manager**: uv (use `uv sync` for dependencies, `uv run` to execute tools)
- **Testing**: pytest (scenarios require `-m scenario` marker and are skipped in CI)
- **Linting/Formatting**: Ruff (Python), Prettier (JSON), mdformat (Markdown)
- **Type checking**: Pyright

## Agent behavioral rules

These rules apply to all AI agent interactions with this codebase:

### Design principles

**Convention over configuration**: Prefer uniform patterns that work the same everywhere over configurable options that require case-by-case logic.
When code paths diverge based on metadata flags or configuration, ask whether the divergence is necessary.
Often, a single convention that handles all cases uniformly is simpler and more maintainable.

- Derive behavior from existing structure rather than adding metadata flags
- Make all instances of a pattern work the same way - no special cases
- Let upstream validation (e.g., config flows) enforce constraints so downstream code can assume valid data
- Config flows use `vol.Required()` and `vol.Optional()` to enforce required fields at entry time
- Downstream code (coordinator, adapters) can assume required fields are present because config flow guarantees it
- For optional values, if they are missing or None, skip them uniformly throughout processing

**Composition over complexity**: Build features by composing simple, focused components rather than adding conditional logic to existing code.
Each component should do one thing well without needing to know about the internals of other components.

- Separate concerns: validation happens at config flow boundaries, processing assumes valid input
- Avoid "check if X then do Y else do Z" patterns - instead, make X and Y go through the same code path
- When adding a feature, prefer creating new simple components over adding branches to existing ones
- Runtime code uses the result of schema validation, not the schema itself - the schema's job is done at configuration time

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

### Code review guidelines

When reviewing code, rely on linting tools (Ruff and Pyright) to identify issues that they can detect.
Do not report on issues that these tools already catch, such as:

- Unused imports
- Type errors
- Style violations
- Formatting issues
- Other issues detectable by static analysis tools

Focus review comments on:

- Logic errors and bugs
- Architectural concerns
- Performance issues
- Security vulnerabilities
- Code clarity and maintainability
- Missing tests or documentation

This avoids false positives and redundant feedback that linting tools already provide.

## Universal code standards

- **Python**: 3.13+ with modern features (pattern matching, `str | None` syntax, f-strings, dataclasses)
- **Type hints**: Required on all functions, methods, and variables
- **Typing philosophy**: Type at boundaries, use TypedDict/TypeGuard for narrowing, prefer types over runtime checks
- **Formatting**: Ruff (Python), Prettier (JSON), mdformat (Markdown)
- **Linting**: Ruff
- **Type checking**: Pyright
- **Language**: American English for all code, comments, and documentation
- **Testing**: pytest with coverage enforced by codecov on changed lines

See [typing philosophy](../docs/developer-guide/typing.md) for detailed type patterns.

### Units

Use SI-derived units scaled for numerical stability:

- Power: kilowatts (kW)
- Energy: kilowatt-hours (kWh)
- Time: hours (model layer) / seconds (rest of code)

The model layer uses hours for time to keep LP solver values in the ideal range.
The rest of the codebase uses seconds for time (Home Assistant convention).
See [units guide](../docs/developer-guide/units.md) for rationale.

### Subentry naming conventions

When working with element subentries:

- `subentry.title` MUST match the element's `name` field
- `subentry.subentry_type` MUST match the element's `element_type` field
- In `participants` dictionaries, keys represent element names (matching `subentry.title`)

These invariants are enforced throughout the codebase and must be maintained.

### Translation and naming conventions

HAEO follows Home Assistant's entity naming conventions for sensor translations.
See `.github/instructions/translations.instructions.md` for detailed rules.

### Version matching

The version number must be consistent across:

- `pyproject.toml` (`version = "x.y.z"`)
- `custom_components/haeo/manifest.json` (`"version": "x.y.z"`)

When updating version numbers, update both files together.

Key patterns for sensor display names using sentence case (capital first letter, rest lowercase):

1. **Power sensors**: Action + noun pattern ("Import power", "Charge power")
2. **Price sensors**: Qualifier + price pattern ("Import price", "Export price")
3. **Shadow price sensors**: Constraint + "shadow price" suffix ("Max import power shadow price")
4. **Connection sensors**: Use parameterized translations with `{source}` and `{target}` placeholders

Avoid special characters in translation display names as they are used in entity ID generation.

## Path-specific instructions

This repository uses path-specific instruction files in `.github/instructions/` that apply additional context based on the files being edited.

| Instruction File                                                                    | Applies To                                    | When To Use                                                                                    |
| ----------------------------------------------------------------------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [config-flow.instructions.md](.github/instructions/config-flow.instructions.md)     | `**/config_flow.py`, `**/flows/**`            | Developing config flows, element configuration UI, schema generation, validation logic         |
| [documentation.instructions.md](.github/instructions/documentation.instructions.md) | `docs/**`                                     | Writing or updating user guides, developer documentation, modeling docs, adding examples       |
| [elements.instructions.md](.github/instructions/elements.instructions.md)           | `custom_components/haeo/elements/**`          | Creating or modifying element adapters, schema/data types, field metadata                      |
| [integration.instructions.md](.github/instructions/integration.instructions.md)     | `custom_components/haeo/**`                   | Home Assistant integration patterns, coordinator usage, entity development, exception handling |
| [manifest.instructions.md](.github/instructions/manifest.instructions.md)           | `**/manifest.json`                            | Updating integration metadata, dependencies, version requirements                              |
| [meta.instructions.md](.github/instructions/meta.instructions.md)                   | `.github/instructions/**`, `.cursor/rules/**` | Maintaining instruction files themselves, updating rules based on feedback                     |
| [model.instructions.md](.github/instructions/model.instructions.md)                 | `custom_components/haeo/model/**`             | Developing LP model elements, constraints, cost functions, optimization logic                  |
| [python.instructions.md](.github/instructions/python.instructions.md)               | `**/*.py`                                     | All Python code - type hints, async patterns, error handling, code style                       |
| [scenarios.instructions.md](.github/instructions/scenarios.instructions.md)         | `tests/scenarios/**`                          | Creating or maintaining end-to-end scenario tests with realistic data                          |
| [tests.instructions.md](.github/instructions/tests.instructions.md)                 | `tests/**`                                    | Writing unit tests, integration tests, test fixtures, coverage requirements                    |
| [translations.instructions.md](.github/instructions/translations.instructions.md)   | `**/translations/**`                          | Adding or updating user-facing strings, sensor names, error messages                           |

**Note**: The `python.instructions.md` file applies to all Python files and provides universal Python coding standards.
Other instruction files provide domain-specific guidance that builds upon these universal standards.

## Documentation

- [Documentation guidelines](../docs/developer-guide/documentation-guidelines.md) - Writing and maintaining docs
- [Units guide](../docs/developer-guide/units.md) - Unit conversion and conventions
- [Testing guide](../docs/developer-guide/testing.md) - Test patterns and scenarios

## Self-maintenance

When the user provides feedback about systemic corrections (coding patterns, style issues, architectural decisions, or recurring mistakes), update the appropriate instruction file to capture that feedback for future sessions.

See `.github/instructions/meta.instructions.md` for guidance on maintaining both Copilot instructions and Cursor rules in sync.

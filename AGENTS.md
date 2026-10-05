# HAEO agent instructions

This repository contains **HAEO** (Home Assistant Energy Optimizer) - a Python 3.13+ Home Assistant custom component for energy network optimization using linear programming.

## Project overview

HAEO optimizes energy usage across battery storage, grid import/export, loads, and generators using linear programming.
The integration provides real-time optimization based on energy prices, forecasts, and system constraints.

### Core components

The integration follows a layered architecture:

- **Model layer** (`core/model/`): LP formulation with elements, constraints, and cost functions
- **Elements layer** (`elements/`, `core/schema/`, `core/adapters/`): Element registry, schemas, and adapters
- **Coordinator** (`coordinator/`): Orchestrates data loading, optimization, and result extraction
- **Entities** (`sensor.py`, `number.py`, `switch.py`, `entities/`): Expose inputs and optimization results to Home Assistant
- **Config flows** (`flows/`): Subentry-based configuration for hub and elements

See [architecture guide](docs/developer-guide/architecture.md) for detailed component interactions.

### Project structure

```
custom_components/haeo/     # Home Assistant integration
├── core/                   # Core infrastructure (no HA dependencies)
│   ├── model/              # LP model (constraints, variables, optimization)
│   ├── data/               # Data loading utilities and forecast extractors
│   ├── schema/             # Element schemas, field types, sections, migrations
│   └── adapters/           # Element adapters and policy compilation
├── elements/               # Element registry, availability, input field derivation
├── flows/                  # Hub, options, and element config flows
│   └── elements/           # Per-element flow implementations
├── coordinator/            # Optimization cycle and network assembly
├── entities/               # Entity classes behind the sensor, number, and switch platforms
├── horizon.py              # Forecast time windows
├── input_stores.py         # Input store layer backing the input entities
└── translations/           # i18n strings (en.json)
tools/                      # Developer CLIs (check, diag, sim, snapshot)
tests/scenarios/            # End-to-end scenario tests
docs/                       # Documentation
```

Tests are colocated with source code in `tests/` subdirectories within each package.
The top-level `tests/` directory holds only scenario tests, guide tests, and CLI tool tests.
`custom_components/haeo/sensors/` contains tests, not an implementation.

The `core/` package must never import Home Assistant; import-linter enforces this.

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

### Commit messages

Use plain English commit messages without conventional commit prefixes (`feat:`, `fix:`, `refactor:`, etc.).
Write a short summary line in imperative mood, followed by a blank line and bullet points if needed.

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

See [typing philosophy](docs/developer-guide/typing.md) for detailed type patterns.

### Units

Use SI-derived units scaled for numerical stability:

- Power: kilowatts (kW)
- Energy: kilowatt-hours (kWh)
- Time: hours (model layer) / seconds (rest of code)

The model layer uses hours for time to keep LP solver values in the ideal range.
The rest of the codebase uses seconds for time (Home Assistant convention).
See [units guide](docs/developer-guide/units.md) for rationale.

### Subentry naming conventions

When working with element subentries:

- `subentry.title` MUST match the element's `name` field
- `subentry.subentry_type` MUST match the element's `element_type` field
- In `participants` dictionaries, keys represent element names (matching `subentry.title`)

These invariants are enforced throughout the codebase and must be maintained.

### Translation and naming conventions

HAEO follows Home Assistant's entity naming conventions for sensor translations.
The `translations` skill has the detailed rules.

### Version matching

The version number must be consistent across:

- `pyproject.toml` (`version = "x.y.z"`)
- `custom_components/haeo/manifest.json` (`"version": "x.y.z"`)

When updating version numbers, update both files together, then run `uv sync` to regenerate `uv.lock`.

Key patterns for sensor display names using sentence case (capital first letter, rest lowercase):

1. **Power sensors**: Action + noun pattern ("Import power", "Charge power")
2. **Price sensors**: Qualifier + price pattern ("Import price", "Export price")
3. **Shadow price sensors**: Constraint + "shadow price" suffix ("Max import power shadow price")
4. **Connection sensors**: Use parameterized translations with `{source}` and `{target}` placeholders

Avoid special characters in translation display names as they are used in entity ID generation.

## Skills

Detailed standards and workflows live in `.agents/skills/`, one directory per skill, each with a `SKILL.md`.
They follow the [Agent Skills](https://agentskills.io) open standard, so Copilot, Cursor, Claude Code, Codex, and other compatible agents all read the same files.

Skills load on demand: an agent sees only each skill's name and description until a task matches, then reads the full instructions.
That means **the description decides whether the rule is followed at all**.
Write descriptions that name the subject and say when to use it.

Read the skill covering an area before changing code in it.
`python` and `integration` apply to nearly all work in this repository.

## Verification

Run `uv run check` before considering work complete.
It runs every CI job that can run locally — ruff, pyright, import boundaries, mdformat, prettier, version consistency, unit tests, scenario tests, and frontend card checks — in about 65 seconds.
`--fast` runs ruff, pyright, and unit tests in about 35.
`hassfest` and HACS validation have no local equivalent and run only in GitHub Actions.

Tests run under `timeout = 5` per test with `filterwarnings = ["error"]`, so a new warning is a hard failure and a hang surfaces as a 5-second timeout.

## Documentation

- [Documentation guidelines](docs/developer-guide/documentation-guidelines.md) - Writing and maintaining docs
- [Units guide](docs/developer-guide/units.md) - Unit conversion and conventions
- [Testing guide](docs/developer-guide/testing.md) - Test patterns and scenarios

## Self-maintenance

When the user provides feedback about systemic corrections (coding patterns, style issues, architectural decisions, or recurring mistakes), update the appropriate instruction file to capture that feedback for future sessions.

The `agent-setup` skill explains how the skills are organized and how to add one.

---
description: Update documentation based on code changes in the current branch compared to main
---

# Update Documentation Based on Branch Changes

Analyze the differences between the current branch and the `main` branch, then update the relevant documentation to reflect all code changes.

## Step 1: Analyze Git Changes

First, identify what has changed:

1. **Get the diff**: Compare the current branch to `main` using `git diff main...HEAD` or `git diff main HEAD`
2. **Categorize changes**:
   - New features (new files, new functions, new classes)
   - Modified features (changed behavior, updated APIs)
   - Deleted features (removed functionality)
   - Bug fixes (behavior corrections)
   - Refactoring (internal changes without behavior changes)

3. **Map changes to documentation areas**:
   - **User-facing changes** → `docs/user-guide/` (configuration, usage, examples)
   - **Developer-facing changes** → `docs/developer-guide/` (architecture, APIs, extension points)
   - **Model/mathematical changes** → `docs/modeling/` (LP formulation, constraints, cost functions)
   - **Element-specific changes** → Both user-guide and modeling docs for that element

## Step 2: Documentation Update Strategy

For each identified change, determine what documentation needs updating:

### New Features

- **New elements**: Create documentation in both `docs/user-guide/elements/` and `docs/modeling/device-layer/` (and `model-layer/` if applicable)
  - Use templates from `docs/developer-guide/templates/` as starting points
  - Follow element documentation patterns from existing elements
- **New configuration options**: Update relevant element pages in `docs/user-guide/elements/`
- **New sensors**: Document in element pages and update `docs/user-guide/forecasts-and-sensors.md` if behavior changes
- **New developer APIs**: Document in `docs/developer-guide/` with architecture focus, not code reproduction

### Modified Features

- **Changed behavior**: Update all documentation that describes the old behavior
- **New parameters**: Add to configuration documentation with examples
- **Deprecated features**: Note deprecation and migration path
- **API changes**: Update developer documentation, link to source code for details

### Deleted Features

- **Removed functionality**: Remove or mark as deprecated in documentation
- **Breaking changes**: Document migration path and rationale

## Step 3: Follow Documentation Guidelines

When updating documentation, strictly follow the guidelines in `docs/developer-guide/documentation-guidelines.md`:

### Core Principles

- **Minimalism first**: Keep explanations short and purposeful
- **Match audience**: User docs for UI tasks, developer docs for architecture
- **Link to Home Assistant**: Reference [HA developer docs](https://developers.home-assistant.io/) for standard concepts
- **No unverified claims**: Avoid quantitative performance statements without benchmarks
- **Consistent terminology**: Use "Hub", "Element", "Connection", "Sensor" as defined

### Formatting Requirements

- **Semantic line breaks**: One sentence per line, optional breaks at clause boundaries
- **Sentence case**: All headings use sentence case
- **American English**: Use American spelling throughout
- **Backticks**: Use for file paths, filenames, variable names, field entries

### DRY Principle

- **Link, don't duplicate**: Reference existing authoritative sources rather than repeating information
- **Single source of truth**:
  - Forecasts/sensors → `docs/user-guide/forecasts-and-sensors.md`
  - Units → `docs/developer-guide/units.md`
  - Home Assistant concepts → Link to HA developer docs
- **Progressive disclosure**: High-level pages describe patterns, detail pages provide specifics

### User-Facing Pages

- **Next Steps section**: All user-facing pages must end with a Next Steps section using Material grid cards format
- **Actionable content**: Provide clear instructions or outcomes for every step
- **No code samples**: Avoid code in user-facing docs (except configuration YAML examples)

### Developer-Facing Pages

- **Architecture focus**: Explain design intent, extension points, and reasoning
- **Link to source**: Point to GitHub source files rather than copying code
- **Conceptual explanations**: Describe algorithms conceptually, not line-by-line

### Diagrams

- **Use mermaid**: All diagrams must use mermaid format
- **Semantic colors**: Use default styling (blue for general, green for generation, red for consumption, yellow for grid/pricing)
- **Appropriate chart types**: Flowcharts for topology, XY charts for time series, state diagrams for modes

## Step 4: Documentation Structure Mapping

Map code changes to specific documentation locations:

### Element Changes

If changes affect an element type (battery, grid, solar, load, node, connection, etc.):

1. **User guide**: `docs/user-guide/elements/{element}.md`
   - Configuration fields
   - Examples
   - Sensors created
   - Troubleshooting

2. **Modeling docs**:
   - `docs/modeling/device-layer/{element}.md` (if device-layer element)
   - `docs/modeling/model-layer/elements/{element}.md` (if model-layer element)
   - `docs/modeling/model-layer/connections/{connection}.md` (if connection)

3. **Developer guide**: `docs/developer-guide/` (if architecture or extension points change)

### Integration Changes

If changes affect core integration behavior:

1. **User guide**: `docs/user-guide/configuration.md`, `docs/user-guide/optimization.md`, etc.
2. **Developer guide**: `docs/developer-guide/architecture.md`, `docs/developer-guide/coordinator.md`, etc.

### Data Loading Changes

If changes affect data loading or sensors:

1. **User guide**: `docs/user-guide/forecasts-and-sensors.md`
2. **Developer guide**: `docs/developer-guide/data-loading.md`

## Step 5: Consistency Checks

Before finalizing documentation updates:

- [ ] **Terminology**: Verify consistent use of "Hub", "Element", "Connection", "Sensor"
- [ ] **Units**: Power in kW, energy in kWh, prices in $/kWh, time in seconds (internal) or hours (user-facing)
- [ ] **Links**: Test all internal links resolve correctly
- [ ] **Cross-references**: Update links to changed sections
- [ ] **Next Steps**: Ensure user-facing pages have Next Steps sections
- [ ] **Templates**: Use templates for new element documentation
- [ ] **Progressive disclosure**: High-level pages describe patterns, not enumerate implementations

## Step 6: Update Process

1. **Read existing docs**: Understand current documentation structure and style
2. **Identify gaps**: Determine what's missing or outdated
3. **Update systematically**: Work through each affected documentation area
4. **Maintain consistency**: Follow existing patterns and conventions
5. **Verify links**: Check that all internal and external links work
6. **Review formatting**: Ensure semantic line breaks and proper markdown structure

## Output

Provide a summary of:
- Files changed in the branch
- Documentation files updated
- New documentation files created (if any)
- Key changes made to each documentation file
- Any documentation that may need manual review

Focus on accuracy, consistency, and adherence to HAEO documentation standards.

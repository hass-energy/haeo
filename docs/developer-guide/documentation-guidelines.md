# Documentation Guidelines

This guide describes how to write and maintain HAEO documentation.
It ensures every contribution stays consistent with Home Assistant practices and keeps the docs approachable for all audiences.

## Core principles

### Minimalism first

Keep explanations short and purposeful.
Prefer a brief outline plus links to deeper references rather than long narratives.
Remove anything that restates information better maintained elsewhere (code comments, release notes, upstream docs).

### Match content to the audience

**User-focused documentation** covers tasks in the Home Assistant UI, expected inputs, and what readers can do with the results.
Avoid code samples, deep implementation detail, or configuration storage notes in user spaces.

**Developer-focused documentation** explains design intent, extension points, and reasoning.
Point to source files when implementation specifics are needed rather than copying code into the docs.

### Link to Home Assistant concepts

Whenever a concept exists in the [Home Assistant developer documentation](https://developers.home-assistant.io/docs/documenting/integration-docs-examples), link directly to it.
Do not duplicate explanations of config entries, coordinators, config flows, or other platform features.
Use local documentation only for HAEO-specific behaviour.

### No unverified performance claims

Avoid quantitative statements such as "solves in 5 seconds" unless backed by published benchmarks that we keep up to date.
Describe performance qualitatively: explain how users can monitor it and which levers they can adjust.

### Consistent terminology

Refer to HAEO components using shared labels:

- **Hub** for the primary integration entry
- **Element** for batteries, grids, photovoltaics, loads, and nodes
- **Connection** for power flow links between elements
- **Sensor** for Home Assistant entities created by HAEO

Only mention a specific element type within its own page or a dedicated comparison table.
Elsewhere, favour neutral language such as "elements" or "devices".

## Authoring workflow

1. Confirm the correct target audience and choose the right section of the docs.
2. Outline the information in short bullet points before drafting paragraphs.
3. Write using semantic line breaks: one sentence per line, optional additional breaks at clause boundaries for clarity.
4. Insert links to HA resources when referencing standard concepts.
5. Provide actionable instructions or outcomes for every step the reader must take.
6. Perform a proofread focused on clarity for non-native English speakers.
7. Run the link checks and consistency review listed below before submitting changes.

## Link checking

- Use `mkdocs serve` or `mkdocs build` to surface warnings about missing pages.
- Manually click each new or updated internal link to confirm it resolves.
- Verify external Home Assistant links still lead to maintained content.
- Replace redirected URLs with their final destinations.

## DRY principle for documentation

**Don't Repeat Yourself** applies to documentation as much as code.
When information exists in one authoritative location, link to it rather than duplicating.

### Single source of truth

Establish primary references for cross-cutting concepts:

- **Forecasts and sensors**: `docs/user-guide/forecasts-and-sensors.md` is the authoritative source for sensor behavior, data extraction, multiple sensors, forecast cycling, and supported formats
- **Units**: `docs/developer-guide/units.md` covers unit conversion and base units
- **Home Assistant concepts**: Link to [HA developer docs](https://developers.home-assistant.io/) for standard platform concepts (ConfigEntry, DataUpdateCoordinator, Entity, etc.)

### When to duplicate vs link

**Link when:**

- The concept is explained thoroughly elsewhere
- The information changes independently (implementation details, API references)
- The target audience differs (user vs developer documentation)

**Duplicate when:**

- The information is element-specific (battery SOC limits vs grid import limits)
- Context is essential for understanding (brief inline examples)

## Cross-referencing strategy

Effective cross-references guide readers without overwhelming them.

### Link text best practices

- Use descriptive link text: "See the [Forecasts and Sensors guide](../user-guide/forecasts-and-sensors.md)" not "See [here](#)"
- Inline field type links: `**Forecast** | [sensor(s)](../user-guide/forecasts-and-sensors.md)` in configuration tables
- Reference specific sections when helpful: "[Forecast Cycling](../user-guide/forecasts-and-sensors.md#forecast-coverage-and-cycling)"

### Avoiding circular references

- User guides should link to reference documentation, not vice versa
- Element pages link to the forecasts guide; the forecasts guide doesn't enumerate all elements
- Developer guides can reference user guides for context, but focus on architecture not usage

### Cross-reference maintenance

When updating a primary reference:

- Search for links to that page across the documentation
- Verify links still point to correct sections (especially after heading changes)
- Update inline descriptions if the linked content's scope changed

## Technical accuracy checklist

Before committing documentation changes, verify:

### Units and measurements

- [ ] Power uses kW (kilowatts), not W or MW
- [ ] Energy uses kWh (kilowatt-hours), not Wh or MWh
- [ ] Prices use \$/kWh, not cents or other currencies
- [ ] Time uses seconds for internal timestamps, hours for user-facing durations
- [ ] All numeric examples use realistic values

### Sensor behavior

- [ ] Sensors provide EITHER present value OR forecast, never both
- [ ] Multiple sensors combine additively (sum at each timestamp)
- [ ] Forecast cycling uses natural period alignment, not arbitrary repetition
- [ ] Interpolation is trapezoidal (interval averages), not point sampling

### Implementation details

- [ ] Sensor field types link to forecasts-and-sensors.md
- [ ] Code examples match actual implementation (verify against source)
- [ ] Configuration examples use valid YAML structure
- [ ] Sensor naming matches actual output (e.g., `power_imported` not `import_power`)

## Next steps requirements

All user-facing pages must end with a **Next Steps** section.

### Purpose

Next Steps sections help users discover related topics and continue their learning journey.
They prevent dead-ends and guide users toward completing common workflows.

### Structure

Use Material for MkDocs grid cards format (match `docs/index.md`):

```markdown
## Next Steps

<div class="grid cards" markdown>

-   :material-icon:{ .lg .middle } **Card title**

    ---

    Brief description of what the user will learn or accomplish.

    [:material-arrow-right: Link text](path/to/page.md)

</div>
```

### Content guidelines

- **3 cards maximum**: More creates choice paralysis
- **Logical progression**: Next steps should flow naturally from current page content
- **Actionable descriptions**: Focus on what users will do or learn, not just topic names
- **Appropriate icons**: Use Material icons that match the topic (`:material-battery-charging:`, `:material-chart-line:`, etc.)

### Examples of good Next Steps

From photovoltaics configuration:

1. Connect to network (logical next action after configuring an element)
2. Understand sensor loading (deepens understanding of the Forecast field)
3. Add battery storage (common use case combining elements)

From forecasts and sensors guide:

1. Configure specific elements (apply knowledge to real configuration)
2. Understand optimization (see how forecast data affects results)
3. Troubleshooting (address common issues)

## Code in developer docs

Developer documentation explains architecture and design decisions, not implementation details.

### What to include

- **High-level architecture**: Component responsibilities, interactions, data flow
- **Design rationale**: Why decisions were made, alternatives considered, trade-offs
- **Extension points**: How to add new features (new parsers, new element types)
- **Key concepts**: Algorithms explained conceptually (trapezoidal integration purpose, not formula)

### What to avoid

- **Code reproduction**: Don't copy class definitions, function signatures, or implementation logic
- **Line-by-line explanations**: Readers can view source code if they need that detail
- **Detailed examples**: Brief conceptual examples are fine, but not exhaustive test cases

### Linking to source code

When referencing implementation:

- Link to the specific module on GitHub: [`TimeSeriesLoader`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/data/loader/time_series_loader.py)
- Reference function/class names in text: "The `combine_sensor_payloads()` function merges multiple sensors..."
- Describe purpose and behavior, not implementation: "combines additively" not "loops through payloads and sums values"

### When code examples are appropriate

Use code snippets when:

- Showing API usage patterns (how to call the loader, not how it's implemented)
- Demonstrating test patterns (structure, not exhaustive cases)
- Illustrating external interfaces (config schema, sensor attributes)

Keep snippets minimal and focused on the concept being explained.

## Consistency review

- Confirm terminology matches the glossary above.
- Compare duplicate topics (for example, battery configuration vs battery modeling) to ensure they complement rather than repeat one another.
- Ensure every user-facing page ends with a **Next Steps** section that links to the most relevant follow-up topics, and refresh those links whenever nearby content changes.
- Match the **Next Steps** layout in `docs/index.md`.
    Use a Material grid, apply `{ .lg .middle }` to the icon, follow with a descriptive sentence, and finish with an arrow-link call to action.
- Summarise directory layouts at a high level; avoid listing every file because those inventories fall out of date quickly.
- Make sure each page introduces a concept once and references it elsewhere instead of re-explaining it.
- Check that tables share consistent column ordering and naming.
- Ensure screenshots, diagrams, or examples use the same element names throughout the docs.

## Progressive disclosure

Progressive disclosure organizes information from general concepts to specific details.
It keeps high-level documentation stable while allowing implementation details to evolve.

### Principles

**High-level pages describe patterns, not implementations:**

- Overview pages explain architectural concepts without enumerating every concrete type
- Use generic terms: "elements" instead of listing "battery, grid, photovoltaics, loads, nodes"
- Describe aggregation patterns: "elements contribute constraints" not "battery has SOC constraint, grid has power limit"
- Point to detail pages rather than duplicating their content

**Detail pages provide specifics:**

- Element-specific pages enumerate their exact constraints, variables, and parameters
- Implementation guides show concrete examples
- API references list actual method signatures

### Examples of progressive disclosure

**❌ Bad: Enumeration in overview**

> HAEO supports batteries, grids, photovoltaics, constant loads, forecast loads, and nodes.
> Batteries have state of charge constraints.
> Grids have import and export limits.
> Photovoltaics have generation forecasts.

This becomes outdated when element types change.

**✅ Good: Pattern description in overview**

> HAEO models energy systems as networks of elements connected by power flows.
> Each element contributes decision variables, constraints, and costs to the optimization problem.
> See the [element documentation](../user-guide/elements/index.md) for specific element types.

This remains stable as implementations evolve.

**❌ Bad: Implementation details in architecture**

> The `Network` class has methods `add_battery()`, `add_grid()`, `add_photovoltaics()`, etc.

This requires updates whenever element types change.

**✅ Good: Pattern description in architecture**

> The `Network` class aggregates constraints from all elements via their `constraints()` method.
> Elements register themselves during the `add()` process.

This explains the pattern without enumerating implementations.

### When to use progressive disclosure

**Use in:**

- Index pages (`modeling/index.md`, `user-guide/elements/index.md`)
- Architecture overviews
- Getting started guides
- High-level concept explanations

**Don't use in:**

- Element-specific pages (be concrete about battery behavior)
- API references (list actual methods)
- Troubleshooting guides (reference specific error messages)
- Configuration examples (show real YAML)

## Templates

HAEO provides living templates that can be copied and adapted when creating new documentation.
These templates ensure consistent structure across element documentation.

### Available templates

**[Element user guide template](templates/element-user-guide-template.md)**

Use when documenting user-facing configuration for a new element type.
Includes sections for configuration fields, examples, sensors created, and troubleshooting.

**[Element modeling template](templates/element-modeling-template.md)**

Use when documenting the mathematical formulation of a new element type.
Includes sections for decision variables, parameters, constraints, cost functions, and physical interpretation.

### Using templates

1. Copy the appropriate template file from `docs/developer-guide/templates/`
2. Rename to match your element: `battery.md`, `grid.md`, etc.
3. Replace all `[Element Name]` placeholders with the actual element name
4. Fill in each section following the guidance provided in the template
5. Remove any guidance comments before committing

### Template customization

Templates provide a consistent structure, but not every section is required for every element:

- Skip sections that don't apply (some elements may not have troubleshooting issues)
- Add subsections when needed for clarity
- Reorder content within sections if it improves flow
- Document intentional deviations in pull request descriptions

The goal is consistency where it helps readers, not rigid adherence to structure.

## Submission checklist

Before opening a pull request:

- [ ] Audience and tone verified against the target section
- [ ] Links tested and updated
- [ ] Terminology and naming consistent with existing pages
- [ ] No quantitative performance claims without benchmarks
- [ ] Templates applied or intentionally adapted with justification in the PR description
- [ ] No duplicate information (checked against primary references)
- [ ] Technical details verified for accuracy (units, sensor behavior, implementation)
- [ ] User-facing pages include Next Steps sections
- [ ] Developer documentation focuses on architecture, not code reproduction

Following these guidelines keeps HAEO documentation lean, accurate, and easy to maintain.

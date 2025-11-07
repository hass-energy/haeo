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

## Consistency review

- Confirm terminology matches the glossary above.
- Compare duplicate topics (for example, battery configuration vs battery modeling) to ensure they complement rather than repeat one another.
- Ensure every user-facing page ends with a **Next steps** callout that links to the most relevant follow-up topics, and refresh those links whenever nearby content changes.
- Match the **Next steps** layout in `docs/index.md`.
    Use a Material grid, apply `{ .lg .middle }` to the icon, follow with a descriptive sentence, and finish with an arrow-link call to action.
- Summarise directory layouts at a high level; avoid listing every file because those inventories fall out of date quickly.
- Make sure each page introduces a concept once and references it elsewhere instead of re-explaining it.
- Check that tables share consistent column ordering and naming.
- Ensure screenshots, diagrams, or examples use the same element names throughout the docs.

## Templates

Use these templates when creating new pages so readers encounter familiar structures.
Adjust sections only when the content truly needs a different flow.

### Element user guide template

```markdown
# [Element Name] Configuration

Brief description (1-2 sentences).

## Configuration Fields

Table of fields with descriptions.

## Configuration Example

Minimal example without detailed explanations.

## Sensors Created

Table of sensors.

## Troubleshooting

Common issues and solutions.

## Related Documentation

Links only.
```

### Element modeling template

```markdown
# [Element Name] Modeling

Brief description.

## Model Formulation

### Decision Variables
### Parameters
### Constraints
### Cost Contribution

## Physical Interpretation

Conceptual explanation without worked examples.

## Related Documentation

Links only.
```

## Submission checklist

Before opening a pull request:

- [ ] Audience and tone verified against the target section
- [ ] Links tested and updated
- [ ] Terminology and naming consistent with existing pages
- [ ] No quantitative performance claims without benchmarks
- [ ] Templates applied or intentionally adapted with justification in the PR description

Following these guidelines keeps HAEO documentation lean, accurate, and easy to maintain.

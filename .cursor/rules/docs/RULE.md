---
description: "Documentation standards"
globs: ["docs/**"]
alwaysApply: false
---

# Documentation standards

See @docs/developer-guide/documentation-guidelines.md for comprehensive guidelines.

## Core principles

- **DRY**: Link to source code instead of duplicating implementation details
- **Guide, don't duplicate**: Explain concepts and locations, not line-by-line code
- **Link to Home Assistant**: Reference [HA docs](https://developers.home-assistant.io/) for standard concepts

## Semantic line breaks

Use one sentence per line following [SemBr specification](https://sembr.org/):

```markdown
All human beings are born free and equal in dignity and rights.
They are endowed with reason and conscience.
```

Break lines at semantic boundaries:
- **Required**: After sentences (., !, ?)
- **Recommended**: After independent clauses (,, ;, :, —)
- **Optional**: After dependent clauses for clarity

**Never break lines based on column count.**

## Formatting

- Use backticks for: file paths, filenames, variable names, field entries
- Sentence case for all headings
- American English spelling

## Diagrams

Use mermaid for all diagrams:
- Flowcharts for network topology
- XY charts for time series data
- State diagrams for operational modes

## Next steps sections

All user-facing pages must end with a **Next Steps** section using Material grid cards:

```markdown
## Next steps

<div class="grid cards" markdown>

-   :material-battery:{ .lg .middle } **Configure battery**

    ---

    Set up battery storage for your network.

    [:material-arrow-right: Battery setup](elements/battery.md)

</div>
```

## Cross-references

- Use descriptive link text: "See the [Forecasts guide](forecasts.md)"
- Reference specific sections when helpful
- User guides link to reference docs, not vice versa

## What to avoid

- Duplicating implementation details from code
- Quantitative performance claims without benchmarks
- Line-by-line code explanations
- Plain text file names without links when mentioning specific files

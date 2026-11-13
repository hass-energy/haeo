---
name: documentation
description: Documentation standards for docs/ and the zensical site built from mkdocs.yml — semantic line breaks, sentence case headings, mermaid diagrams, Next steps grid cards on user pages, link-don't-duplicate, and the strict build that fails on broken links and anchors. Use when writing or updating any user guide, developer guide, walkthrough, or modeling page.
---

# Documentation standards

[documentation-guidelines.md](../../../docs/developer-guide/documentation-guidelines.md) is the full guide; this is the checklist.

## Building

The site is built by [zensical](https://zensical.org/), which reads `mkdocs.yml`:

```bash
uv run zensical serve   # live preview
uv run zensical build   # what the docs gate runs
```

**The build fails on a broken link or anchor.**
`mkdocs.yml` sets `strict: true`, so a relative link to a missing page or a `#anchor` that matches no heading stops the build and names the file and line.
External links are not checked.

Markdown is formatted by mdformat and JSON by Prettier; `uv run check --fix` applies both.

## Writing

- One sentence per line ([semantic line breaks](https://sembr.org/)); never wrap by column count.
- Sentence case for every heading.
- American English.
- Backticks for file paths, names, and field keys.
- Describe the docs as things are, never what they used to be.

## Link, don't duplicate

- Describe a module by its role and link to the source file rather than reproducing code or long file lists that drift.
- Link to the [Home Assistant developer docs](https://developers.home-assistant.io/) for standard concepts.
- Do not enumerate element kinds or build per-element tables outside an element's own page.
    Describe the pattern and point at the registry; each element's page covers itself.
- Make no quantitative performance claim without a benchmark.

## Diagrams

Use mermaid: flowcharts for topology, XY charts for time series, state diagrams for modes.

## Next steps

User-facing pages end with a `## Next steps` section of Material grid cards.
Developer pages may omit it, but any that exist must link to real pages.

```markdown
## Next steps

<div class="grid cards" markdown>

-   :material-battery:{ .lg .middle } **Configure battery**

    ---

    Set up battery storage for your network.

    [:material-arrow-right: Battery setup](elements/battery.md)

</div>
```

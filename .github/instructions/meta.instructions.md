---
applyTo: .github/instructions/**,.cursor/rules/**
description: Meta-rules for maintaining instruction and rule files
globs: [.github/instructions/**, .cursor/rules/**]
alwaysApply: false
---

# Meta-rules for instruction maintenance

This file governs how to maintain the instruction and rule files themselves.

## Dual system architecture

HAEO uses parallel AI instruction systems that share the same source files:

- **GitHub Copilot**: `.github/instructions/*.instructions.md` (source files)
- **Cursor**: `.cursor/rules/*/RULE.mdc` (symlinks to source files)

Additionally, HAEO uses a reusable prompts system for chat commands:

- **GitHub Copilot**: `.github/prompts/*.prompt.md` (source files)
- **Cursor**: `.cursor/commands/` (symlink to `.github/prompts/`)

### Combined frontmatter

All instruction files use combined frontmatter containing both Copilot and Cursor formats:

```yaml
applyTo: glob/pattern/**
description: Rule description
globs: [glob/pattern/**]
alwaysApply: false
```

This allows Cursor rules to be symlinks to the Copilot instruction files.

### Current symlink structure

Each Cursor rule directory contains a `RULE.mdc` symlink pointing to the corresponding Copilot instruction:

| Cursor Rule       | Symlink Target                                         |
| ----------------- | ------------------------------------------------------ |
| `haeo/RULE.mdc`   | `../../../.github/copilot-instructions.md`             |
| `python/RULE.mdc` | `../../../.github/instructions/python.instructions.md` |
| `model/RULE.mdc`  | `../../../.github/instructions/model.instructions.md`  |
| (etc.)            | (etc.)                                                 |

The prompts system uses a single symlink:

| Cursor Location     | Symlink Target       |
| ------------------- | -------------------- |
| `.cursor/commands/` | `../.github/prompts` |

## Keeping systems in sync

Since Cursor rules are symlinks, updating a Copilot instruction automatically updates the corresponding Cursor rule.
No manual synchronization is needed.

When adding a new instruction file:

1. Create the file in `.github/instructions/` with combined frontmatter
2. Create the corresponding directory in `.cursor/rules/`
3. Create a symlink: `ln -s ../../../.github/instructions/name.instructions.md .cursor/rules/name/RULE.mdc`

When adding a new prompt file:

1. Create the file in `.github/prompts/` with `.prompt.md` extension
2. Include optional YAML frontmatter with `description` field
3. The file is automatically accessible via the `.cursor/commands/` symlink
4. Use the prompt in chat by typing `/filename` (without the `.prompt.md` extension)

## Self-maintenance process

When the user provides feedback about systemic corrections:

1. **Identify scope**: Is this Python-specific? Integration-specific? Project-wide?
2. **Find target files**: Match to the appropriate instruction/rule files
3. **Check for duplicates**: Ensure this isn't already covered elsewhere
4. **Add actionable guideline**: Write as a directive
5. **Update both systems**: Update both Copilot instruction AND Cursor rule

## Rule content guidelines

### Use semantic line breaks

All instruction files should follow semantic line break conventions.
One sentence per line, with optional breaks at clause boundaries for clarity.

### Don't enumerate groups

When providing guidance about a category of things, describe the category pattern rather than listing members.
Enumeration creates brittle rules that become outdated when the codebase changes.

```markdown
<!-- ❌ Bad: Enumeration -->
Each element (Battery, Grid, Load, Solar, Node) must have...

<!-- ✅ Good: Pattern description -->
Each element type registered in ELEMENT_TYPES must have...
```

The test for good grouping: if you can't identify the group without enumerating it, it's not a well-defined group.

### Actionable content

Every rule must be something the agent can act on.
Remove marketing text and feature lists without guidance.

### Explanatory background

Background context is allowed when it improves decision-making.
"We use uv" is useful context; "uv is fast" is marketing.

### Concise

Keep each rule file focused.
If a rule file exceeds ~500 lines, consider splitting.

### DRY

Link to documentation for detailed explanations.
Rules contain directives; docs contain explanations.

## What makes a good rule

| ✅ Good Rule                                 | ❌ Bad Rule                                         |
| -------------------------------------------- | --------------------------------------------------- |
| "Use `str \| None` not `Optional[str]`"      | "Python has several ways to express optional types" |
| "Keep try blocks minimal"                    | "Error handling is important"                       |
| "Use `asyncio.gather()` for multiple awaits" | "Async programming has many benefits"               |
| "Elements are registered in ELEMENT_TYPES"   | "Battery, Grid, Load, PV, Node are elements"        |

## When to update rules vs documentation

| Update Rules When...               | Update Docs When...                |
| ---------------------------------- | ---------------------------------- |
| Adding a new directive             | Explaining why a pattern exists    |
| Changing a coding standard         | Providing extended examples        |
| Adding anti-patterns to avoid      | Documenting architecture decisions |
| Agent-specific behavioral guidance | Human-readable tutorials           |

## File format reference

### Copilot instructions

```markdown
---
applyTo: "glob/pattern/**"
---

# Title

Content...
```

### Cursor rules

```markdown
---
description: "Brief description"
globs: ["glob/pattern/**"]
alwaysApply: false
---

# Title

Content...
```

### Reusable prompts

```markdown
---
description: Brief description of what the prompt does
---

# Prompt Title

Instructions for the AI agent...
```

Prompt files use `.prompt.md` extension and are stored in `.github/prompts/`.
They are accessible in both VSCode (via `.github/prompts/`) and Cursor (via `.cursor/commands/` symlink).

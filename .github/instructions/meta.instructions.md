---
applyTo: ".github/instructions/**,.cursor/rules/**"
---

# Meta-rules for instruction maintenance

This file governs how to maintain the instruction and rule files themselves.

## Dual system architecture

HAEO uses two parallel AI instruction systems:
- **GitHub Copilot**: `.github/instructions/*.instructions.md`
- **Cursor**: `.cursor/rules/*/RULE.md`

Both systems should contain equivalent actionable content for their respective scopes.

## Keeping systems in sync

When updating a rule in one system, update the corresponding rule in the other:

| Copilot Instruction | Cursor Rule |
|---------------------|-------------|
| `python.instructions.md` | `python/RULE.md` |
| `model.instructions.md` | `model/RULE.md` |
| `elements.instructions.md` | `elements/RULE.md` |
| `integration.instructions.md` | `integration/RULE.md` |
| `config-flow.instructions.md` | `config-flow/RULE.md` |
| `manifest.instructions.md` | `manifest/RULE.md` |
| `translations.instructions.md` | `translations/RULE.md` |
| `tests.instructions.md` | `tests/RULE.md` |
| `scenarios.instructions.md` | `scenarios/RULE.md` |
| `documentation.instructions.md` | `docs/RULE.md` |
| `meta.instructions.md` | `meta/RULE.md` |
| (main copilot-instructions.md) | `haeo/RULE.md` |

## Self-maintenance process

When the user provides feedback about systemic corrections:

1. **Identify scope**: Is this Python-specific? Integration-specific? Project-wide?
2. **Find target files**: Match to the appropriate instruction/rule files
3. **Check for duplicates**: Ensure this isn't already covered elsewhere
4. **Add actionable guideline**: Write as a directive, not explanation
5. **Update both systems**: Update both Copilot instruction AND Cursor rule

## Rule content guidelines

### Actionable only

Every rule must be something the agent can act on. Remove:
- Marketing text ("10-100x faster")
- Explanatory background
- Feature lists without guidance

### Concise

Keep each rule file focused. If a rule file exceeds ~500 lines, consider splitting.

### DRY

Link to documentation for detailed explanations. Rules contain directives; docs contain explanations.

### No duplication within a system

Each guideline lives in ONE rule file per system. Other rules reference it.

## What makes a good rule

| ✅ Good Rule | ❌ Bad Rule |
|-------------|-----------|
| "Use `str \| None` not `Optional[str]`" | "Python has several ways to express optional types" |
| "Keep try blocks minimal" | "Error handling is important" |
| "Target >95% test coverage" | "Testing is valuable" |
| "Use `asyncio.gather()` for multiple awaits" | "Async programming has many benefits" |

## When to update rules vs documentation

| Update Rules When... | Update Docs When... |
|---------------------|---------------------|
| Adding a new directive | Explaining why a pattern exists |
| Changing a coding standard | Providing extended examples |
| Adding anti-patterns to avoid | Documenting architecture decisions |
| Agent-specific behavioral guidance | Human-readable tutorials |

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

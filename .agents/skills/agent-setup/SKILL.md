---
name: agent-setup
description: How this repository's agent instructions are organized as Agent Skills, and how to add or change them. Use when editing AGENTS.md or anything under .agents/skills/, or when the user gives feedback about coding patterns, style, or recurring mistakes that should be captured for future sessions.
---

# Maintaining the agent instructions

This file governs the instruction system itself.

## Layout

There is one source of truth for each kind of guidance, and everything else is a symlink:

```
AGENTS.md                      # repository-wide rules, always loaded
.agents/skills/<name>/SKILL.md # everything else, loaded on demand
CLAUDE.md      -> AGENTS.md
.claude/skills -> ../.agents/skills
```

`AGENTS.md` and `.agents/skills/` are the [Agent Skills](https://agentskills.io) open standard, so Copilot, Cursor, Codex, Gemini CLI, and other compatible agents read them directly with no per-tool configuration.
Claude Code does not yet look in `.agents/`, which is the only reason the two symlinks exist.
When it gains support, delete them.

There are deliberately no Copilot `applyTo` globs, Cursor rules, or reusable prompt files.
Those were per-tool formats for the same content; skills replaced all of them.

## Permission grants stay out of the repository

`.claude/settings.json` and `.claude/settings.local.json` are gitignored, and no equivalent for any other agent belongs in version control either.

An allowlist entry for anything that executes project code — `pytest`, `uv run`, the gate runner — is arbitrary code execution for an agent that can also edit that code.
Committing one silently grants that to everyone who clones the repository, in environments that may not be sandboxed like the author's.
Whether to pre-approve a command is a per-developer, per-environment trust decision, so leave it to the developer.

Skills may describe what a command does and when to run it.
They must not try to arrange for it to run without a prompt.

## How skills load

Agents read only each skill's `name` and `description` at startup, then load the full body when a task matches.
**The description decides whether the skill is used at all.**
A perfect skill with a vague description never fires.

Write descriptions that state the subject and the trigger, using the words someone would naturally use for the task:

```yaml
description: User-facing strings in translations/en.json — sensor and device 
  display names, entity translation keys, config flow errors, exception and 
  repair issue messages. Use when adding or renaming any user-visible string, 
  entity name, or output sensor.
```

Name concrete files, directories, and domain nouns.
Avoid descriptions that only restate the skill name.

## Adding a skill

1. Create `.agents/skills/<name>/SKILL.md` with `name` and `description` frontmatter.
    The `name` must match the directory.
2. Write the body as directives an agent can act on.
3. Nothing else.
    Discovery is automatic in every agent, and the Claude Code symlink already covers the whole tree.

A skill directory may also hold `scripts/`, `references/`, and `assets/` for material the body links to.
Keep the body short and push bulk reference material into those files, so it costs nothing until needed.

Executable tooling that humans also run belongs in `tools/`, not inside a skill.

## Choosing where guidance goes

| Put it in   | When                                                                      |
| ----------- | ------------------------------------------------------------------------- |
| `AGENTS.md` | It applies to essentially every change, or an agent must know it up front |
| A skill     | It applies to one area, task, or workflow                                 |
| `docs/`     | A human needs the explanation, not just the directive                     |

`AGENTS.md` is loaded in full on every request, so keep it short.
If a section of it has grown into a procedure, move it into a skill.

## Self-maintenance

When the user gives feedback about a systemic correction — a coding pattern, a style issue, an architectural decision, a recurring mistake:

1. **Identify scope**: which area does it belong to?
2. **Find the target**: the matching skill, or `AGENTS.md` if it is universal
3. **Check for duplicates**: make sure it is not already covered elsewhere
4. **Write it as a directive**: something an agent can act on, not a description of the problem

## Content guidelines

### Use semantic line breaks

One sentence per line, with optional breaks at clause boundaries for clarity.

### Don't enumerate groups

Describe the category pattern rather than listing members.
Enumeration creates brittle rules that go stale as the codebase changes.

```markdown
<!-- ❌ Bad: Enumeration -->

Each element (Battery, Grid, Load, Solar, Node) must have...

<!-- ✅ Good: Pattern description -->

Each element type registered in ELEMENT_TYPES must have...
```

The test for good grouping: if you cannot identify the group without enumerating it, it is not a well-defined group.

Descriptions are the exception.
Listing concrete names there helps an agent decide whether the skill is relevant, which is the whole job of that field.

### Actionable content

Every rule must be something an agent can act on.
Remove marketing text and feature lists without guidance.

### Explanatory background

Background context is allowed when it improves decision-making.
"We use uv" is useful context; "uv is fast" is marketing.

### Concise

Keep each skill focused.
If one exceeds ~500 lines, split it or move reference material into `references/`.

### DRY

Link to documentation for detailed explanations.
Skills contain directives; docs contain explanations.

## What makes a good rule

| ✅ Good rule                                 | ❌ Bad rule                                         |
| -------------------------------------------- | --------------------------------------------------- |
| "Use `str \| None` not `Optional[str]`"      | "Python has several ways to express optional types" |
| "Keep try blocks minimal"                    | "Error handling is important"                       |
| "Use `asyncio.gather()` for multiple awaits" | "Async programming has many benefits"               |
| "Elements are registered in ELEMENT_TYPES"   | "Battery, Grid, Load, PV, Node are elements"        |

## When to update skills vs documentation

| Update a skill when...             | Update docs when...                |
| ---------------------------------- | ---------------------------------- |
| Adding a new directive             | Explaining why a pattern exists    |
| Changing a coding standard         | Providing extended examples        |
| Adding anti-patterns to avoid      | Documenting architecture decisions |
| Agent-specific behavioral guidance | Writing human-readable tutorials   |

## Keeping skills honest

Skills that describe code drift as the code changes, and a confidently wrong skill is worse than no skill.
When a skill's claims are contradicted by the code, fix the skill in the same change.
Prefer describing where things live and what the contracts are over reproducing code that will move.

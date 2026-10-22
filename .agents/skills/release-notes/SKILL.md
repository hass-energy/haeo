---
name: release-notes
description: Generate structured release notes from the pull requests between two versions, split into user-facing and developer-facing changes. Use when preparing a GitHub release or when asked for a changelog.
---

# Release notes

Generate release notes for a HAEO release.

## Process

1. **Gather context**: Identify the version being released and the previous version to compare against
2. **Collect PR information**: Pull requests are squash merged with the PR number in the subject, so `git log --oneline <previous-tag>..<target>` lists them (tags look like `v0.4.1`); GitHub's auto-generated release notes give the same list with authors
3. **Analyze key PRs**: For major features, examine PR descriptions and file changes to understand the scope and user impact
4. **Categorize changes**: Group into user-facing vs. developer-facing, features vs. fixes vs. improvements

## Output structure

Use this structure for the release notes:

### Highlights

- 2-4 bullet points with emoji icons summarizing the most impactful changes
- Focus on what users will experience and benefit from
- Describe outcomes, not implementation details (e.g., "5x faster" not "refactored to declarative architecture")
- If there are significant developer-facing changes, add a separate **Developer highlights** subsection within Developer-facing changes

### Breaking changes

- Include only when there are any, immediately after Highlights and before User-facing changes
- Use ⚠️ emoji in section header for visibility
- Clearly describe what changed and why it might affect users
- Provide migration instructions: what users need to do to adapt
- Be specific about entity names, API changes, or configuration format changes

### User-facing changes

- **New features**: Visible functionality users can interact with
- **Configuration improvements**: UX/workflow improvements
- **Bug fixes**: Issues that affected users

### Developer-facing changes

- **Developer highlights**: Major architectural achievements that developers will appreciate (optional, only for significant changes)
- **Architecture**: Internal refactors, performance improvements, structural changes
- **Schema and API changes**: Changes to internal systems developers work with
- **Testing and documentation**: Improvements to developer experience

### Contributors

- List all contributors with GitHub handles
- Highlight first-time contributors with 🎉

### Full changelog

- Include the complete list of PRs with links
- Use GitHub's auto-generated format with PR numbers and author attributions

## Guidelines

- User-facing changes come before developer-facing changes
- Most important changes appear first within each section
- Include PR numbers as references (e.g., #186)
- Be specific about what changed, not just that something changed
- **Highlights must describe user benefits, not implementation**: Users care that optimization is faster, not that it uses warm start or declarative patterns
- **Breaking changes go at the top**: If there are breaking changes, they must appear immediately after Highlights so users see them first
- Implementation details belong in Developer-Facing Changes where developers can appreciate them
- Output as a markdown file ready to paste into GitHub releases

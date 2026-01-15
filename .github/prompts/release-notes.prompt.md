---
description: Generate structured release notes from GitHub PRs between two versions
---

Generate comprehensive release notes for a software release.

## Process

1. **Gather context**: Identify the version being released and the previous version to compare against
2. **Collect PR information**: Use GitHub's auto-generated release notes or git log to identify all changes between versions
3. **Analyze key PRs**: For major features, examine PR descriptions and file changes to understand the scope and user impact
4. **Categorize changes**: Group into user-facing vs. developer-facing, features vs. fixes vs. improvements

## Output Structure

Use this structure for the release notes:

### Highlights (User-Facing)

- 2-4 bullet points with emoji icons summarizing the most impactful changes
- Focus on what users will experience and benefit from
- Describe outcomes, not implementation details (e.g., "5x faster" not "refactored to declarative architecture")
- If there are significant developer-facing changes, add a separate **Developer Highlights** subsection within Developer-Facing Changes

### Breaking Changes (if any)

- Place immediately after Highlights, before User-Facing Changes
- Use ⚠️ emoji in section header for visibility
- Clearly describe what changed and why it might affect users
- Provide migration instructions: what users need to do to adapt
- Be specific about entity names, API changes, or configuration format changes

### User-Facing Changes

- **New Features**: Visible functionality users can interact with
- **Configuration Improvements**: UX/workflow improvements
- **Bug Fixes**: Issues that affected users

### Developer-Facing Changes

- **Developer Highlights**: Major architectural achievements that developers will appreciate (optional, only for significant changes)
- **Architecture**: Internal refactors, performance improvements, structural changes
- **Schema/API Changes**: Changes to internal systems developers work with
- **Testing & Documentation**: Improvements to developer experience

### Contributors

- List all contributors with GitHub handles
- Highlight first-time contributors with 🎉

### Full Changelog

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

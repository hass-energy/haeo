# Contributing to HAEO

Thank you for your interest in contributing!

## Development workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linters and tests
6. Submit a pull request

## Code standards

- **Python 3.14+** required
- **Type hints** on all functions
- **Docstrings** (Google style)
- **Tests** for new features
- **Ruff** formatting

### Type safety guidelines

HAEO uses Python's type system to make invalid states impossible.
Follow these guidelines when writing code:

**Use type assertions for architectural invariants:**

```python
from custom_components.haeo.elements import assert_config_entry_exists

# ✅ Good: Type assertion for controlled data
hub_entry = assert_config_entry_exists(
    hass.config_entries.async_get_entry(hub_entry_id),
    hub_entry_id,
)

# ❌ Bad: Defensive logging for controlled data
hub_entry = hass.config_entries.async_get_entry(hub_entry_id)
if not hub_entry:
    _LOGGER.warning("Hub entry not found")
    return
```

**Keep defensive checks for external boundaries:**

```python
# ✅ Good: Defensive handling of external API responses
try:
    data = await api.get_forecast()
except ApiError as err:
    _LOGGER.error("Failed to fetch forecast: %s", err)
    return None

# ✅ Good: Defensive handling of Home Assistant state
state = hass.states.get(entity_id)
if state is None:
    _LOGGER.warning("Entity %s not found", entity_id)
    return None
```

**When to use each approach:**

| Situation                   | Approach               | Why                                                |
| --------------------------- | ---------------------- | -------------------------------------------------- |
| Config entry we created     | Type assertion         | We control the ID, missing = programming error     |
| Config flow validated data  | Type assertion         | Validation guaranteed, missing = programming error |
| Element type from registry  | Type assertion         | Registry defines valid types                       |
| External API response       | Defensive check + test | API can fail, legitimate runtime condition         |
| Home Assistant entity state | Defensive check + test | Entity might not exist, user-caused                |
| User input (initial)        | Defensive check + test | User can provide invalid data                      |

See [Testing Guide](testing.md#type-safety-over-defensive-tests) for detailed examples.

## Testing

```bash
uv run pytest
uv run ruff check
uv run pyright
```

All checks must pass before merging.

## Documentation

Update documentation for:

- New features
- Configuration changes
- API modifications

### Markdown formatting

Write all markdown files using semantic line breaks.
Follow the [Semantic Line Breaks specification (SemBr)](https://sembr.org/).
This makes git diffs cleaner and pull request reviews easier.

**Guidelines:**

- Break lines after each sentence (., !, ?)
- Break lines after independent clauses when it improves clarity (,, ;, :, —)
- Break lines before lists
- **Never break lines based on column count or character limits**
- Break lines only at semantic boundaries
- If a line exceeds ~120 characters, it's likely a sign that the prose needs simplification or restructuring

**Example:**

```markdown
All human beings are born free and equal in dignity and rights.
They are endowed with reason and conscience and should act towards one another in a spirit of brotherhood.
```

The rendered output remains unchanged,
but the source is easier to edit and review.

### Building documentation

Build docs locally:

```bash
uv run zensical serve
```

## Pull request process

1. Run `uv run check` and fix anything it reports
2. Update the documentation the change affects
3. Open the pull request and request review

Release notes are written from the merged pull requests, so describe the change in the pull request rather than in a changelog file.

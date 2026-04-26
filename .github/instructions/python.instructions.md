---
applyTo: '**/*.py'
description: Python coding standards for HAEO
globs: ['**/*.py']
alwaysApply: false
---

# Python coding standards

## Language requirements

- Python 3.13+ required
- Use modern features:
    - Pattern matching (`match`/`case`)
    - Type hints with modern union syntax: `str | None` not `Optional[str]`
    - f-strings (preferred over `%` or `.format()`)
    - Dataclasses for data containers
    - Walrus operator (`:=`) where it improves readability

## Type hints

- Add type hints to ALL functions, methods, and variables
- Use modern union syntax: `str | None` not `Optional[str]`
- Use `type` aliases for complex types:
    ```python
    type MyConfigEntry = ConfigEntry[MyClient]
    ```

## Typing philosophy

Type objects at boundaries as early as possible.
Use TypedDict and TypeGuard to narrow types early and use throughout.
Prefer the type system over runtime checks - tests should never verify things the type checker can identify.

See [typing philosophy](../../docs/developer-guide/typing.md) for detailed patterns.

## Async programming

- All external I/O must be async
- Avoid `await` in loops - use `asyncio.gather()` instead:
    ```python
    # ❌ Bad
    for item in items:
        await process(item)

    # ✅ Good
    await asyncio.gather(*[process(item) for item in items])
    ```
- Never block the event loop:
    - Use `asyncio.sleep()` not `time.sleep()`
    - Use executor for blocking I/O: `await hass.async_add_executor_job(fn, args)`
- Use `@callback` decorator for event loop safe functions

## Error handling

- **Fail loudly**: Never log an error/warning and continue as if nothing happened.
    If something fails that should succeed, raise an exception. Silent failures hide bugs.
- **Use HA-specific exceptions** in setup flows instead of generic Python exceptions:
    - `ConfigEntryNotReady` - Transient error (network timeout, service unavailable). HA will retry setup.
    - `ConfigEntryError` - Permanent failure (invalid config). User must fix configuration.
    - `ConfigEntryAuthFailed` - Authentication failure. User must re-authenticate.
    - `UpdateFailed` - Coordinator refresh failed. Used in `_async_update_data`.
    ```python
    # ❌ Bad - generic exception in async_setup_entry
    try:
        await client.fetch()
    except TimeoutError:
        raise TimeoutError("Setup timed out") from None

    # ✅ Good - HA-specific exception enables proper retry behavior
    from homeassistant.exceptions import ConfigEntryNotReady

    try:
        await client.fetch()
    except TimeoutError:
        raise ConfigEntryNotReady("Setup timed out") from None
    ```
- Keep try blocks minimal - only wrap code that can throw:
    ```python
    # ✅ Good
    try:
        data = await client.get_data()
    except ClientError:
        _LOGGER.error("Failed to fetch data")
        return

    # Process data outside try block
    processed = data.value * 100
    ```
- Avoid bare `except Exception:` except in:
    - Config flows (for robustness)
    - Background tasks
- Chain exceptions with `from`:
    ```python
    try:
        data = await client.fetch()
    except ApiError as err:
        raise UpdateFailed("API error") from err
    ```

## Logging

- No periods at end of messages
- No integration names (added automatically)
- No sensitive data (keys, tokens, passwords)
- Use lazy logging:
    ```python
    _LOGGER.debug("Processing data: %s", variable)
    ```
- Debug level for non-user-facing messages

## Code style

- Formatting: Ruff
- Linting: Ruff
- Type checking: Pyright
- American English for all code and comments
- Sentence case for messages

### Lint suppressions

`# noqa` is a tool of last resort.
Before adding one, try to restructure the code so the lint rule is satisfied naturally.
Only suppress when there is genuinely no reasonable alternative.

Every `# noqa` comment must include an explicit reason explaining why the suppression is necessary and why the code cannot be restructured to avoid it.
The reason goes in parentheses after the rule code:

```python
# ✅ Good - genuine need with reason
raise ValueError(msg)  # noqa: TRY004 (ValueError is appropriate here, not TypeError)

# ❌ Bad - no reason
raise ValueError(msg)  # noqa: TRY004

# ❌ Bad - could have been avoided by restructuring
from .foo import bar  # noqa: PLC0415 (only needed here)
# ↑ If the import works at module level, just move it there
```

**Exception for deferred imports (PLC0415)**: Ruff's isort (`force-sort-within-sections`) strips inline reasons from import lines.
For PLC0415, put the reason on the preceding comment line and keep the noqa bare.
The reason must explain a genuine constraint (circular import, conditional availability, etc.) — not just preference:

```python
# ✅ Good - genuine circular import, reason on preceding line
# Avoid circular import with parent package
from .internals import _private  # noqa: PLC0415

# ❌ Bad - no actual constraint, just move it to module level
# Only used in one function
from .internals import _private  # noqa: PLC0415
```

## Docstrings

- Required for all public functions and methods
- Short and concise file headers:
    ```python
    """Battery element for energy network optimization."""
    ```
- Method docstrings describe what, not how:
    ```python
    async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
        """Set up HAEO from a config entry."""
    ```

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

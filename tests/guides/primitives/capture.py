"""Screenshot collection context for guide automation.

Provides hierarchical screenshot naming through a context stack.
Screenshots are named based on the function call hierarchy, e.g.:
    add_grid.select_entity.Import_Price.search
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path
from typing import Any

# Module-level holder for the current context
_current_context: list[ScreenshotContext | None] = [None]


@dataclass
class ScreenshotContext:
    """Context for collecting screenshots with hierarchical naming.

    Screenshots are stored in an OrderedDict with keys like:
        "add_grid.fill_textbox.Grid_Name"
        "add_grid.select_entity.Import_Price.search"

    The naming hierarchy is built from:
    1. The decorated function name (e.g., "add_grid")
    2. The HAPage method name (e.g., "select_entity")
    3. The element/field name (e.g., "Import_Price")
    4. Optional step suffix (e.g., "search", "result")
    """

    output_dir: Path
    screenshots: OrderedDict[str, Path] = field(default_factory=OrderedDict)
    _stack: list[str] = field(default_factory=list)
    _step_number: int = 0

    @staticmethod
    def current() -> ScreenshotContext | None:
        """Get the current active context."""
        return _current_context[0]

    @staticmethod
    def require() -> ScreenshotContext:
        """Get the current context, raising if none is active."""
        ctx = _current_context[0]
        if ctx is None:
            msg = "No ScreenshotContext is active"
            raise RuntimeError(msg)
        return ctx

    def push(self, name: str) -> None:
        """Push a name onto the context stack."""
        self._stack.append(name)

    def pop(self) -> None:
        """Pop a name from the context stack."""
        if self._stack:
            self._stack.pop()

    def capture(self, page: Any, step: str) -> Path:
        """Capture a screenshot with hierarchical naming.

        Args:
            page: Playwright page object
            step: Step name within current context (e.g., "click", "result")

        Returns:
            Path to the saved screenshot

        """
        self._step_number += 1

        # Build hierarchical name from stack + step
        # Sanitize names: replace spaces with underscores, remove special chars
        parts = [self._sanitize(p) for p in self._stack]
        parts.append(self._sanitize(step))
        name = ".".join(parts)

        # Include step number for ordering
        filename = f"{self._step_number:03d}_{name}.png"
        path = self.output_dir / filename

        page.screenshot(path=str(path), animations="disabled")
        self.screenshots[name] = path

        return path

    @staticmethod
    def _sanitize(name: str) -> str:
        """Sanitize a name for use in filenames."""
        # Replace spaces and special chars with underscores
        result = name.replace(" ", "_").replace("-", "_")
        # Remove any remaining problematic characters
        return "".join(c for c in result if c.isalnum() or c == "_")

    @contextmanager
    def scope(self, name: str) -> Iterator[None]:
        """Context manager to add a scope level."""
        self.push(name)
        try:
            yield
        finally:
            self.pop()


@contextmanager
def screenshot_context(output_dir: Path) -> Iterator[ScreenshotContext]:
    """Create a screenshot collection context.

    Usage:
        with screenshot_context(output_dir) as ctx:
            add_integration(page, "My System")
            add_battery(page, ...)
            # ctx.screenshots contains all captured screenshots

    """
    output_dir.mkdir(parents=True, exist_ok=True)
    ctx = ScreenshotContext(output_dir=output_dir)

    previous = _current_context[0]
    _current_context[0] = ctx
    try:
        yield ctx
    finally:
        _current_context[0] = previous


def guide_step[F: Callable[..., Any]](func: F) -> F:
    """Wrap a guide function to push its name onto the screenshot context stack.

    All screenshots taken within the function get hierarchical names.

    Usage::

        @guide_step
        def add_battery(page: HAPage, name: str, ...):
            page.fill_textbox("Battery Name", name)  # → "add_battery.fill_textbox.Battery_Name"
            ...

    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        ctx = ScreenshotContext.current()
        if ctx is None:
            # No context active, just call the function
            return func(*args, **kwargs)

        with ctx.scope(func.__name__):
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]

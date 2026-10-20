"""Screenshot collection context for guide automation.

Provides hierarchical screenshot naming through a context stack.
Screenshots are named based on the function call hierarchy, e.g.:
    001_add_grid.select_entity.Import_Price.search.png
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from playwright.sync_api import Page

from tools.live_hass import wait_for_requests

_WAIT_SETTLED_JS = (Path(__file__).parent / "js" / "wait_settled.js").read_text()

# How long a page may take to finish rendering before a capture fails
SETTLE_DEADLINE_MS = 10000

# Every capture is saved once per theme, in a directory named after it
THEMES = ("light", "dark")

# Home Assistant switches theme on this event, as its profile page does.
# It hands the new hass object on to the page, but a dialog keeps the one it
# opened with, since the theme cannot change while a dialog is open in normal
# use. Anything still holding the other theme's hass gets the new one and
# renders again, so what depends on the theme in JavaScript, such as brand
# logos with dark variants, follows it too.
_SET_THEME_JS = """
(dark) => {
    const root = document.querySelector('home-assistant');
    root.dispatchEvent(new CustomEvent('settheme', { detail: { dark } }));
    const visit = (node) => {
        for (const el of node.querySelectorAll('*')) {
            if (el.hass && el.hass.themes?.darkMode !== root.hass.themes.darkMode) {
                el.hass = root.hass;
                el.requestUpdate?.();
            }
            if (el.shadowRoot) visit(el.shadowRoot);
        }
    };
    visit(document);
}
"""
_IS_DARK_JS = "() => document.querySelector('home-assistant').hass.selectedTheme?.dark === true"


def wait_until_settled(page: Page) -> None:
    """Block until the page has finished rendering, with nothing under the pointer.

    The pointer moves off the page first. A browser updates hover state on its
    own schedule after the layout under a still pointer changes, so leaving it
    over the page would show hover highlights in some captures and not others.
    Settling repeats until no HTTP request is left in flight, since a request,
    such as for the script of a panel, changes nothing until it is answered.
    """
    page.mouse.move(-1, -1)
    page.evaluate(_WAIT_SETTLED_JS, SETTLE_DEADLINE_MS)
    while wait_for_requests(page):
        page.evaluate(_WAIT_SETTLED_JS, SETTLE_DEADLINE_MS)


@dataclass
class _ContextHolder:
    """Mutable holder for the module-level screenshot context."""

    current: ScreenshotContext | None = None


_holder = _ContextHolder()


@dataclass
class ScreenshotContext:
    """Context for collecting screenshots with hierarchical naming.

    Screenshots are stored in an OrderedDict keyed by filenames like:
        "001_add_grid.fill_textbox.Grid_Name.png"
        "002_add_grid.select_entity.Import_Price.search.png"

    The logical naming hierarchy is built from:
    1. The decorated function name (e.g., "add_grid")
    2. The HAPage method name (e.g., "select_entity")
    3. The element/field name (e.g., "Import_Price")
    4. Optional step suffix (e.g., "search", "result")

    Filenames add a numeric prefix for ordering, and end in .png for
    screenshots or .svg for figures. Each is saved once per theme, in the
    theme's directory under ``output_dir``.
    """

    output_dir: Path
    screenshots: list[str] = field(default_factory=list)
    _stack: list[str] = field(default_factory=list)
    _step_number: int = 0

    @staticmethod
    def current() -> ScreenshotContext | None:
        """Get the current active context."""
        return _holder.current

    @staticmethod
    def require() -> ScreenshotContext:
        """Get the current context, raising if none is active."""
        ctx = _holder.current
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

    def _next_name(self, step: str, suffix: str) -> str:
        """Return the next numbered filename for a capture in the current scope."""
        self._step_number += 1

        # Build hierarchical name from stack + step
        # Sanitize names: replace spaces with underscores, remove special chars
        parts = [self._sanitize(p) for p in self._stack]
        parts.append(self._sanitize(step))
        name = ".".join(parts)

        # Include step number for ordering and uniqueness
        filename = f"{self._step_number:03d}_{name}{suffix}"
        self.screenshots.append(filename)
        return filename

    def capture(self, page: Page, step: str) -> None:
        """Capture a screenshot in each theme with hierarchical naming.

        The page is captured in the theme it shows first, then switched to
        the other, so consecutive captures switch theme once each.

        Args:
            page: Playwright page object
            step: Step name within current context (e.g., "click", "result")

        """
        filename = self._next_name(step, ".png")

        wait_until_settled(page)
        current = "dark" if page.evaluate(_IS_DARK_JS) else "light"
        for theme in sorted(THEMES, key=lambda theme: theme != current):
            if theme != current:
                page.evaluate(_SET_THEME_JS, theme == "dark")
                wait_until_settled(page)
            page.screenshot(path=str(self.output_dir / theme / filename), animations="disabled")

    def save_figure(self, step: str, render: Callable[[str], str]) -> None:
        """Save a figure, such as a rendered card, as an SVG in each theme with hierarchical naming.

        ``render`` returns the figure's SVG for the theme it is given. Figures
        are shown on their own in the documentation rather than as steps of a
        screenshot slideshow.
        """
        filename = self._next_name(step, ".svg")
        for theme in THEMES:
            (self.output_dir / theme / filename).write_text(render(theme), encoding="utf-8")

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
def pause_screenshots() -> Iterator[None]:
    """Temporarily suppress screenshot capture.

    All guide primitives called within this context will execute normally
    but skip screenshot capture. Used by run_guide() to replay a
    prerequisite guide silently.
    """
    previous = _holder.current
    _holder.current = None
    try:
        yield
    finally:
        _holder.current = previous


@contextmanager
def screenshot_context(output_dir: Path) -> Iterator[ScreenshotContext]:
    """Create a screenshot collection context.

    Usage:
        with screenshot_context(output_dir) as ctx:
            add_integration(page, "My System")
            add_battery(page, ...)
            # ctx.screenshots lists filenames with step prefixes

    """
    for theme in THEMES:
        (output_dir / theme).mkdir(parents=True, exist_ok=True)
    ctx = ScreenshotContext(output_dir=output_dir)

    previous = _holder.current
    _holder.current = ctx
    try:
        yield ctx
    finally:
        _holder.current = previous


def guide_step[F: Callable[..., None]](func: F) -> F:
    """Wrap a guide function to push its name onto the screenshot context stack.

    All screenshots taken within the function get hierarchical names.

    Usage::

        @guide_step
        def add_battery(page: HAPage, name: str, ...):
            page.fill_textbox("Battery Name", name)  # → "add_battery.fill_textbox.Battery_Name"
            ...

    """

    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> None:
        ctx = ScreenshotContext.current()
        if ctx is None:
            # No context active, just call the function
            return func(*args, **kwargs)

        with ctx.scope(func.__name__):
            return func(*args, **kwargs)

    return wrapper  # type: ignore[return-value]

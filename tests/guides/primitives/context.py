"""Guide execution context.

Provides the GuideContext that holds shared state for guide execution
and the guide_context() context manager for setup/teardown.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.sync_api import sync_playwright

from .ha_page import HAPage

if TYPE_CHECKING:
    from collections.abc import Iterator

_LOGGER = logging.getLogger(__name__)


@dataclass
class GuideContext:
    """Execution context for guide steps.

    Holds the HAPage for UI interactions and configuration for the guide run.
    """

    page: HAPage
    output_dir: Path
    config: dict[str, Any]

    @property
    def url(self) -> str:
        """Home Assistant URL."""
        return self.page.url


@contextmanager
def guide_context(
    *,
    url: str,
    output_dir: Path,
    config: dict[str, Any] | None = None,
    headless: bool = True,
    width: int = 800,
    height: int = 600,
) -> Iterator[GuideContext]:
    """Create guide execution context with browser and HA page.

    Args:
        url: Home Assistant URL (e.g., "http://localhost:8123")
        output_dir: Directory for screenshots
        config: Optional configuration dictionary
        headless: Run browser in headless mode
        width: Viewport width
        height: Viewport height

    Yields:
        GuideContext with initialized HAPage

    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": width, "height": height})

        ha_page = HAPage(
            page=page,
            url=url,
            output_dir=output_dir,
        )

        ctx = GuideContext(
            page=ha_page,
            output_dir=output_dir,
            config=config or {},
        )

        try:
            yield ctx
        finally:
            browser.close()
            _LOGGER.info("Guide complete: %d screenshots captured", ha_page.step_number)

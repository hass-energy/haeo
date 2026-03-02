"""Sigenergy system setup guide.

This guide executes the code blocks from the literate guide markdown file.
The markdown file (docs/user-guide/examples/sigenergy-system.md) is the
single source of truth — this module extracts and runs its ```guide blocks.

Run with:
    uv run python tests/guides/sigenergy/guide.py

Screenshots are automatically captured and named hierarchically based on
the function call stack, e.g. "add_battery.entity_Capacity.search_results"
"""

from __future__ import annotations

from collections import OrderedDict
import logging
from pathlib import Path
import shutil
import sys

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant
from tests.guides.primitives import HAPage, screenshot_context
from tools.guide_runner import INPUTS_FILE, _build_exec_namespace, extract_guide_blocks

_LOGGER = logging.getLogger(__name__)

# Paths
GUIDE_DIR = Path(__file__).parent
PROJECT_ROOT = GUIDE_DIR.parent.parent.parent
MARKDOWN_FILE = PROJECT_ROOT / "docs" / "user-guide" / "examples" / "sigenergy-system.md"
SCREENSHOTS_DIR = GUIDE_DIR / "screenshots"


def run_guide(
    hass: LiveHomeAssistant,
    output_dir: Path,
    *,
    headless: bool = True,
    dark_mode: bool = False,
) -> OrderedDict[str, Path]:
    """Run the Sigenergy setup guide from the literate markdown source.

    Extracts ```guide blocks from sigenergy-system.md and executes them
    in sequence against the live HA instance.

    Returns an OrderedDict of screenshot names to paths.
    """
    markdown = MARKDOWN_FILE.read_text(encoding="utf-8")
    blocks = extract_guide_blocks(markdown)

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        hass.inject_auth(context, dark_mode=dark_mode)
        page_obj = context.new_page()
        page_obj.set_default_timeout(5000)

        try:
            page = HAPage(page=page_obj, url=hass.url)
            namespace = _build_exec_namespace(page)

            with screenshot_context(output_dir) as ctx:
                for block in blocks:
                    exec(compile(block.source, f"<guide block {block.index}>", "exec"), namespace)  # noqa: S102

                return ctx.screenshots

        except Exception:
            _LOGGER.exception("Error running guide")
            error_path = output_dir / "error_state.png"
            page_obj.screenshot(path=str(error_path))
            raise

        finally:
            browser.close()


def main() -> None:
    """Run the guide as a standalone script."""
    pause_mode = "--pause" in sys.argv
    headless = not pause_mode

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    _LOGGER.info("Sigenergy System Setup Guide")
    _LOGGER.info("=" * 50)

    if SCREENSHOTS_DIR.exists():
        shutil.rmtree(SCREENSHOTS_DIR)
    SCREENSHOTS_DIR.mkdir(parents=True)

    with live_home_assistant(timeout=120) as hass:
        _LOGGER.info("Home Assistant running at %s", hass.url)
        hass.load_states_from_file(INPUTS_FILE)

        screenshots = run_guide(hass, SCREENSHOTS_DIR, headless=headless)

        _LOGGER.info("=" * 50)
        _LOGGER.info("Guide complete! %d screenshots captured:", len(screenshots))
        for name in screenshots:
            _LOGGER.info("  %s", name)


if __name__ == "__main__":
    main()

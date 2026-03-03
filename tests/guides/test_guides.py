"""Parameterized guide tests.

Discovers markdown files with ```guide code blocks under docs/, extracts
and executes them against a live Home Assistant instance, and captures
screenshots for documentation.

Each guide file is parameterized with light and dark mode variants.
Screenshots are written to the guide's output directory under docs/
(gitignored) so the docs build serves them as static assets.

Run with:
    uv run pytest tests/guides/test_guides.py -m guide -v
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from tests.guides.ha_runner import live_home_assistant
from tools.guide_runner import (
    DOCS_DIR,
    INPUTS_FILE,
    BlockResult,
    GuideManifest,
    compute_page_hash,
    extract_guide_blocks,
    output_dir_for_guide,
    run_blocks_for_mode,
)

_LOGGER = logging.getLogger(__name__)


def _discover_guide_files() -> list[Path]:
    """Find all markdown files under docs/ containing ```guide blocks."""
    guide_files: list[Path] = []
    for md_path in DOCS_DIR.rglob("*.md"):
        content = md_path.read_text(encoding="utf-8")
        if extract_guide_blocks(content):
            guide_files.append(md_path)
    return sorted(guide_files)


GUIDE_FILES = _discover_guide_files()


@pytest.mark.guide
@pytest.mark.enable_socket
@pytest.mark.timeout(300)
@pytest.mark.parametrize("dark_mode", [False, True], ids=["light", "dark"])
@pytest.mark.parametrize(
    "guide_md",
    GUIDE_FILES,
    ids=lambda p: p.stem,
)
def test_guide(guide_md: Path, dark_mode: bool) -> None:
    """Run a guide's code blocks and capture screenshots.

    Each guide markdown file is run in both light and dark mode.
    Screenshots are saved to the guide's output directory under docs/
    so the docs build can serve them as static assets.
    """
    mode = "dark" if dark_mode else "light"
    markdown = guide_md.read_text(encoding="utf-8")
    blocks = extract_guide_blocks(markdown)
    output_dir = output_dir_for_guide(guide_md)

    with live_home_assistant(timeout=120) as hass:
        hass.load_states_from_file(INPUTS_FILE)

        screenshots_per_block = run_blocks_for_mode(hass, blocks, output_dir, mode, headless=True)

    total = sum(len(names) for names in screenshots_per_block)
    assert total > 0, f"No screenshots captured for {guide_md.name} ({mode})"

    # Only write the manifest from the light mode run to avoid
    # the dark mode pass overwriting it with potentially different data.
    if not dark_mode:
        block_results = [
            BlockResult(
                index=block.index,
                content_hash=block.content_hash,
                screenshots=screenshots_per_block[i],
            )
            for i, block in enumerate(blocks)
        ]
        manifest = GuideManifest(
            page_hash=compute_page_hash(blocks),
            viewport={"width": 1280, "height": 800},
            blocks=block_results,
        )
        manifest.save(output_dir / "manifest.json")

    _LOGGER.info(
        "Guide %s (%s): %d blocks, %d screenshots",
        guide_md.stem,
        mode,
        len(blocks),
        total,
    )

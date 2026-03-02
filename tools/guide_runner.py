"""Guide runner: extracts and executes guide code blocks from markdown files.

This module scans markdown files for ```guide fenced code blocks, executes them
sequentially against a live Home Assistant instance via Playwright, and captures
screenshots into per-block directories.

Consecutive code blocks share the same HA + browser context so that state
accumulates across blocks (e.g., add_inverter in block 1, add_battery in block 2).

Usage:
    uv run python -m tools.guide_runner docs/user-guide/examples/sigenergy-system.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import re
import shutil
import sys

from playwright.sync_api import sync_playwright

from tests.guides.ha_runner import LiveHomeAssistant, live_home_assistant
from tests.guides.primitives import (
    ConstantInput,
    EntityInput,
    HAPage,
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    add_load,
    add_node,
    add_solar,
    login,
    screenshot_context,
    verify_setup,
)

_LOGGER = logging.getLogger(__name__)

# Project root for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"

# Regex to extract ```guide blocks from markdown
_GUIDE_BLOCK_RE = re.compile(
    r"^```guide\s*\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class GuideBlock:
    """A single guide code block extracted from markdown.

    Attributes:
        index: Zero-based position of this block in the page.
        source: The Python source code inside the fenced block.
        content_hash: SHA-256 hex digest of the source code.

    """

    index: int
    source: str
    content_hash: str


@dataclass
class BlockResult:
    """Screenshots captured during a single guide block execution.

    Attributes:
        index: Block index matching the GuideBlock.
        content_hash: Hash of the source that produced these screenshots.
        screenshots: List of screenshot filenames (same for both light and dark modes).

    """

    index: int
    content_hash: str
    screenshots: list[str] = field(default_factory=list)


@dataclass
class GuideManifest:
    """Manifest mapping guide blocks to their captured screenshots.

    Attributes:
        page_hash: Combined hash of all block sources for cache invalidation.
        blocks: Per-block screenshot results.

    """

    page_hash: str
    blocks: list[BlockResult]

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict."""
        return {
            "page_hash": self.page_hash,
            "blocks": [
                {
                    "index": b.index,
                    "content_hash": b.content_hash,
                    "screenshots": b.screenshots,
                }
                for b in self.blocks
            ],
        }

    def save(self, path: Path) -> None:
        """Write manifest to disk as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write("\n")

    @staticmethod
    def load(path: Path) -> GuideManifest:
        """Load manifest from disk."""
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return GuideManifest(
            page_hash=data["page_hash"],
            blocks=[
                BlockResult(
                    index=b["index"],
                    content_hash=b["content_hash"],
                    screenshots=b["screenshots"],
                )
                for b in data["blocks"]
            ],
        )


def extract_guide_blocks(markdown: str) -> list[GuideBlock]:
    """Extract all ```guide fenced code blocks from markdown text.

    Returns blocks in document order with their content hashes.
    """
    blocks: list[GuideBlock] = []
    for i, match in enumerate(_GUIDE_BLOCK_RE.finditer(markdown)):
        source = match.group(1)
        content_hash = hashlib.sha256(source.strip().encode()).hexdigest()[:16]
        blocks.append(GuideBlock(index=i, source=source, content_hash=content_hash))
    return blocks


def compute_page_hash(blocks: list[GuideBlock]) -> str:
    """Compute a combined hash of all block sources for cache invalidation."""
    combined = "\n---\n".join(b.source for b in blocks)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def build_exec_namespace(page: HAPage) -> dict[str, object]:
    """Build the namespace dict available to guide code blocks."""
    return {
        "page": page,
        # Field value types
        "EntityInput": EntityInput,
        "ConstantInput": ConstantInput,
        # HAEO element primitives
        "login": login,
        "add_integration": add_integration,
        "add_inverter": add_inverter,
        "add_battery": add_battery,
        "add_solar": add_solar,
        "add_grid": add_grid,
        "add_load": add_load,
        "add_node": add_node,
        "verify_setup": verify_setup,
    }


def output_dir_for_guide(guide_md: Path) -> Path:
    """Return the output directory for a guide's screenshots.

    Screenshots go in a directory named after the markdown file stem,
    as a sibling of the markdown file. This matches MkDocs' directory URL
    convention so relative image paths work in the rendered HTML.
    """
    return guide_md.parent / guide_md.stem


def run_blocks_for_mode(
    hass: LiveHomeAssistant,
    blocks: list[GuideBlock],
    output_dir: Path,
    mode: str,
    *,
    headless: bool = True,
) -> list[list[str]]:
    """Execute all guide blocks in sequence for a single theme mode.

    Returns a list of screenshot filename lists, one per block.
    """
    dark_mode = mode == "dark"
    mode_dir = output_dir / mode

    if mode_dir.exists():
        shutil.rmtree(mode_dir)
    mode_dir.mkdir(parents=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        hass.inject_auth(context, dark_mode=dark_mode)
        page_obj = context.new_page()
        page_obj.set_default_timeout(5000)

        try:
            page = HAPage(page=page_obj, url=hass.url)
            namespace = build_exec_namespace(page)

            # All blocks share one screenshot context (continuous numbering)
            # but we track per-block boundaries
            with screenshot_context(mode_dir) as ctx:
                per_block: list[list[str]] = []

                for block in blocks:
                    # Record screenshots before this block
                    before_count = len(ctx.screenshots)

                    # Execute the block in the shared namespace
                    exec(compile(block.source, f"<guide block {block.index}>", "exec"), namespace)  # noqa: S102

                    # Collect screenshots produced by this block
                    all_names = list(ctx.screenshots.keys())
                    block_names = all_names[before_count:]
                    per_block.append(block_names)

                return per_block

        except Exception:
            _LOGGER.exception("Error running guide block")
            error_path = mode_dir / "error_state.png"
            page_obj.screenshot(path=str(error_path))
            raise

        finally:
            browser.close()


def run_guide_from_markdown(
    markdown_path: Path,
    *,
    headless: bool = True,
    force: bool = False,
) -> GuideManifest:
    """Extract guide blocks from a markdown file and execute them.

    Runs all blocks in both light and dark modes, capturing screenshots.
    Uses content-hash caching: skips execution if the manifest is up to date.

    Args:
        markdown_path: Path to the markdown file containing ```guide blocks.
        headless: Run browser in headless mode.
        force: Force re-execution even if cache is valid.

    Returns:
        GuideManifest with per-block screenshot paths.

    """
    markdown = markdown_path.read_text(encoding="utf-8")
    blocks = extract_guide_blocks(markdown)

    if not blocks:
        _LOGGER.warning("No guide blocks found in %s", markdown_path)
        return GuideManifest(page_hash="empty", blocks=[])

    page_hash = compute_page_hash(blocks)
    output_dir = output_dir_for_guide(markdown_path)
    manifest_path = output_dir / "manifest.json"

    # Check cache
    if not force and manifest_path.exists():
        existing = GuideManifest.load(manifest_path)
        if existing.page_hash == page_hash:
            _LOGGER.info("Guide cache is current for %s, skipping execution", markdown_path.name)
            return existing

    _LOGGER.info("Running guide from %s (%d blocks)", markdown_path.name, len(blocks))

    with live_home_assistant(timeout=120) as hass:
        hass.load_states_from_file(INPUTS_FILE)

        # Run light mode
        _LOGGER.info("Capturing light mode screenshots...")
        light_results = run_blocks_for_mode(hass, blocks, output_dir, "light", headless=headless)

    # Need a fresh HA instance for dark mode (different auth/theme state)
    with live_home_assistant(timeout=120) as hass:
        hass.load_states_from_file(INPUTS_FILE)

        # Run dark mode
        _LOGGER.info("Capturing dark mode screenshots...")
        run_blocks_for_mode(hass, blocks, output_dir, "dark", headless=headless)

    # Build manifest (both modes produce the same filenames)
    block_results = [
        BlockResult(
            index=block.index,
            content_hash=block.content_hash,
            screenshots=light_results[i],
        )
        for i, block in enumerate(blocks)
    ]

    manifest = GuideManifest(page_hash=page_hash, blocks=block_results)
    manifest.save(manifest_path)

    total_screenshots = sum(len(b.screenshots) for b in block_results)
    _LOGGER.info("Guide complete: %d blocks, %d screenshots per mode", len(blocks), total_screenshots)

    return manifest


def main() -> None:
    """CLI entry point: run guide(s) from markdown files."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:  # noqa: PLR2004
        print("Usage: uv run python -m tools.guide_runner <markdown_file> [--force] [--headed]")
        sys.exit(1)

    force = "--force" in sys.argv
    headed = "--headed" in sys.argv
    md_files = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    for md_file in md_files:
        md_path = Path(md_file)
        if not md_path.exists():
            _LOGGER.error("File not found: %s", md_path)
            continue

        run_guide_from_markdown(md_path, headless=not headed, force=force)


if __name__ == "__main__":
    main()

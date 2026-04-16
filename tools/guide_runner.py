"""Guide runner: extracts and executes guide code blocks from markdown files.

This module scans markdown files for ```guide fenced code blocks, executes them
sequentially against a live Home Assistant instance via Playwright, and captures
screenshots into per-block directories.

Consecutive code blocks share the same HA + browser context so that state
accumulates across blocks (e.g., add_inverter in block 1, add_battery in block 2).

Usage:
    uv run python -m tools.guide_runner docs/walkthroughs/sigenergy-system.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
    add_policies,
    add_solar,
    login,
    pause_screenshots,
    reconfigure_policies,
    screenshot_context,
    validate_policies,
    verify_setup,
)
from tools.guide_hashing import compute_content_hash, compute_page_hash, extract_sources

_LOGGER = logging.getLogger(__name__)

# Project root for resolving relative paths
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
INPUTS_FILE = PROJECT_ROOT / "tests" / "scenarios" / "scenario1" / "inputs.json"

# Regex to extract ```guide and ```guide-setup blocks from markdown
_GUIDE_BLOCK_RE = re.compile(
    r"^```guide(?P<setup>-setup)?\s*\n(?P<source>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class GuideBlock:
    """A single guide code block extracted from markdown.

    Attributes:
        index: Zero-based position of this block in the page.
        source: The Python source code inside the fenced block.
        content_hash: SHA-256 hex digest of the source code.
        captures: Whether this block captures screenshots (False for guide-setup).

    """

    index: int
    source: str
    content_hash: str
    captures: bool = True


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
        viewport: Screenshot viewport dimensions {width, height} in pixels.
        blocks: Per-block screenshot results.

    """

    page_hash: str
    viewport: dict[str, int]
    blocks: list[BlockResult]

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-compatible dict."""
        return {
            "page_hash": self.page_hash,
            "viewport": self.viewport,
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
            viewport=data.get("viewport", {"width": 1280, "height": 800}),
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
    """Extract all ```guide and ```guide-setup fenced code blocks from markdown text.

    Returns blocks in document order with page-scoped content hashes.
    Setup blocks have captures=False and are excluded from manifests.
    """
    # First pass: extract sources to compute page hash
    sources = extract_sources(markdown)
    page_hash = compute_page_hash(sources)

    # Second pass: build blocks with page-scoped content hashes
    blocks: list[GuideBlock] = []
    for i, match in enumerate(_GUIDE_BLOCK_RE.finditer(markdown)):
        source = match.group("source")
        is_setup = match.group("setup") is not None
        content_hash = compute_content_hash(page_hash, source)
        blocks.append(GuideBlock(index=i, source=source, content_hash=content_hash, captures=not is_setup))
    return blocks


def get_page_hash(blocks: list[GuideBlock]) -> str:
    """Compute a combined hash of all block sources for cache invalidation.

    Includes both setup and guide blocks since changes to either
    should invalidate the cache.
    """
    return compute_page_hash([b.source for b in blocks])


def _run_guide_silently(page: HAPage, hass: LiveHomeAssistant, guide_name: str) -> None:
    """Execute all guide blocks from another walkthrough without screenshots.

    Loads the referenced guide's markdown, extracts its guide blocks
    (excluding any guide-setup blocks to avoid recursive prerequisites),
    and executes them in a fresh namespace sharing the same page.

    Wraps execution in pause_screenshots() so that even if called from
    a capturing guide block, the prerequisite's actions don't produce
    screenshots attributed to the caller.
    """
    guide_path = DOCS_DIR / "walkthroughs" / f"{guide_name}.md"
    if not guide_path.exists():
        msg = f"Prerequisite guide not found: {guide_path}"
        raise FileNotFoundError(msg)

    markdown = guide_path.read_text(encoding="utf-8")
    ref_blocks = extract_guide_blocks(markdown)

    namespace = build_exec_namespace(page, hass)
    with pause_screenshots():
        for block in ref_blocks:
            if block.captures:
                exec(compile(block.source, f"<{guide_name} block {block.index}>", "exec"), namespace)  # noqa: S102


def build_exec_namespace(page: HAPage, hass: LiveHomeAssistant) -> dict[str, object]:
    """Build the namespace dict available to guide code blocks."""
    return {
        "page": page,
        "hass": hass,
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
        "add_policies": add_policies,
        "reconfigure_policies": reconfigure_policies,
        "validate_policies": validate_policies,
        "verify_setup": verify_setup,
        # Guide chaining
        "run_guide": lambda guide_name: _run_guide_silently(page, hass, guide_name),
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
        browser = p.firefox.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            reduced_motion="reduce",
        )
        hass.inject_auth(context, dark_mode=dark_mode)
        page_obj = context.new_page()
        page_obj.set_default_timeout(5000)

        try:
            page = HAPage(page=page_obj, url=hass.url)
            namespace = build_exec_namespace(page, hass)

            # All blocks share one screenshot context (continuous numbering)
            # but we track per-block boundaries
            with screenshot_context(mode_dir) as ctx:
                per_block: list[list[str]] = []

                for block in blocks:
                    if not block.captures:
                        # Setup blocks run without screenshot capture
                        with pause_screenshots():
                            exec(compile(block.source, f"<guide-setup block {block.index}>", "exec"), namespace)  # noqa: S102
                        continue

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
        return GuideManifest(page_hash="empty", viewport={"width": 1280, "height": 800}, blocks=[])

    page_hash = get_page_hash(blocks)
    output_dir = output_dir_for_guide(markdown_path)
    manifest_path = output_dir / "manifest.json"

    # Check cache
    if not force and manifest_path.exists():
        existing = GuideManifest.load(manifest_path)
        if existing.page_hash == page_hash:
            _LOGGER.info("Guide cache is current for %s, skipping execution", markdown_path.name)
            return existing

    _LOGGER.info("Running guide from %s (%d blocks)", markdown_path.name, len(blocks))

    viewport = {"width": 1280, "height": 800}

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
        dark_results = run_blocks_for_mode(hass, blocks, output_dir, "dark", headless=headless)

    # Validate screenshot parity between modes
    for i, (light_names, dark_names) in enumerate(zip(light_results, dark_results, strict=True)):
        if light_names != dark_names:
            msg = f"Block {i} screenshot mismatch between light and dark modes: light={light_names}, dark={dark_names}"
            raise RuntimeError(msg)

    # Build manifest from capturing blocks only (setup blocks are excluded)
    capturing_blocks = [b for b in blocks if b.captures]
    block_results = [
        BlockResult(
            index=block.index,
            content_hash=block.content_hash,
            screenshots=light_results[i],
        )
        for i, block in enumerate(capturing_blocks)
    ]

    manifest = GuideManifest(page_hash=page_hash, viewport=viewport, blocks=block_results)
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

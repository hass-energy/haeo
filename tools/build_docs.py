"""Build documentation with pre-generated guide screenshots.

Chains two steps:
1. Run guide_runner on all markdown files containing ```guide blocks
2. Invoke mkdocs build (or serve)

Usage:
    uv run python -m tools.build_docs [serve|build] [--force] [--headed]
"""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess
import sys

from tools.guide_runner import extract_guide_blocks, run_guide_from_markdown

_LOGGER = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"


def find_guide_files() -> list[Path]:
    """Find all markdown files under docs/ that contain ```guide blocks."""
    guide_files: list[Path] = []
    for md_path in DOCS_DIR.rglob("*.md"):
        content = md_path.read_text(encoding="utf-8")
        if extract_guide_blocks(content):
            guide_files.append(md_path)
    return guide_files


def run_guides(*, force: bool = False, headed: bool = False) -> None:
    """Execute all guide files to generate screenshots."""
    guide_files = find_guide_files()

    if not guide_files:
        _LOGGER.info("No guide files found")
        return

    _LOGGER.info("Found %d guide file(s):", len(guide_files))
    for path in guide_files:
        _LOGGER.info("  %s", path.relative_to(PROJECT_ROOT))

    for md_path in guide_files:
        output_dir = md_path.parent / md_path.stem
        run_guide_from_markdown(md_path, output_dir, headless=not headed, force=force)


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    args = sys.argv[1:]
    force = "--force" in args
    headed = "--headed" in args
    command_args = [a for a in args if not a.startswith("--")]
    command = command_args[0] if command_args else "build"

    # Step 1: Generate screenshots
    _LOGGER.info("Step 1: Generating guide screenshots...")
    run_guides(force=force, headed=headed)

    # Step 2: Run mkdocs
    _LOGGER.info("Step 2: Running mkdocs %s...", command)
    mkdocs_cmd = ["mkdocs", command]
    result = subprocess.run(mkdocs_cmd, cwd=str(PROJECT_ROOT), check=False)  # noqa: S603
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()

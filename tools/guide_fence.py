"""Custom fence formatter for ``guide`` code blocks.

Renders guide blocks as screenshot slideshows in documentation output.
Used by pymdownx.superfences as a custom fence format function.

Screenshots are loaded from manifest.json files produced by the guide
test suite (``tests/guides/test_guides.py``) or the CLI runner
(``tools/guide_runner``). Manifests are discovered by scanning the
docs directory on first use — no hook or build wrapper needed.

If no manifest exists (e.g., guide tests haven't been run yet),
the code block is rendered as a styled placeholder.

Cross-block continuity: blocks after the first in a page automatically
get the previous block's last screenshot prepended as their first slide,
providing visual continuity between slideshows.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from xml.sax.saxutils import escape

_LOGGER = logging.getLogger(__name__)

_DOCS_DIR = Path(__file__).parent.parent / "docs"


def _load_manifests() -> dict[str, dict[str, object]]:
    """Scan docs/ for manifest.json files and index blocks by content hash.

    Enriches each block with ``_prev_last_screenshot`` — the last screenshot
    filename from the preceding block in the same page manifest, and
    ``_viewport`` — the screenshot viewport dimensions from the manifest.
    """
    index: dict[str, dict[str, object]] = {}

    for manifest_path in _DOCS_DIR.rglob("manifest.json"):
        try:
            with manifest_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            _LOGGER.debug("Skipping invalid manifest: %s", manifest_path)
            continue

        viewport = data.get("viewport", {"width": 1280, "height": 800})
        blocks = data.get("blocks", [])
        for i, block in enumerate(blocks):
            if not isinstance(block, dict) or "content_hash" not in block:
                continue

            # Find the last screenshot of the previous block for carry-over
            prev_last: str | None = None
            if i > 0:
                prev_block = blocks[i - 1]
                prev_screenshots = prev_block.get("screenshots", [])
                if prev_screenshots:
                    prev_last = prev_screenshots[-1]

            block["_prev_last_screenshot"] = prev_last
            block["_viewport"] = viewport
            index[block["content_hash"]] = block

    _LOGGER.debug("Loaded %d guide blocks from manifests", len(index))
    return index


def _find_block(source: str) -> dict[str, object] | None:
    """Find the manifest block matching this source code by content hash."""
    index = _load_manifests()
    content_hash = hashlib.sha256(source.strip().encode()).hexdigest()[:16]
    return index.get(content_hash)


def _screenshot_label(filename: str) -> str:
    """Derive a human-readable label from a screenshot filename.

    Transforms "045_add_battery.fill_Battery_Name.filled.png"
    into "Fill Battery Name".
    """
    # Strip numeric prefix and .png extension
    name = filename.removesuffix(".png")
    # Remove leading NNN_ prefix
    parts = name.split("_", 1)
    if len(parts) > 1 and parts[0].isdigit():
        name = parts[1]

    # Split on dots to get hierarchy parts, take the meaningful ones
    dot_parts = name.split(".")
    # Skip the top-level step name (e.g., "add_battery") and take the rest
    label_parts = dot_parts[1:] if len(dot_parts) > 1 else dot_parts

    # Join and convert underscores to spaces, title case
    label = " ".join(label_parts).replace("_", " ")
    # Title case but keep short words lowercase
    words = label.split()
    if words:
        words[0] = words[0].capitalize()
        label = " ".join(words)

    return label


def _render_slideshow(block: dict[str, object], source: str) -> str:
    """Render a screenshot slideshow for a guide block.

    If the block has a predecessor (non-first block in a page), the
    previous block's last screenshot is prepended as a carry-over slide
    for visual continuity.
    """
    screenshots: list[str] = block.get("screenshots", [])  # type: ignore[assignment]

    if not screenshots:
        return _render_placeholder(source, "No screenshots captured for this block")

    # Build the full slide list with optional carry-over from previous block
    all_screenshots: list[str] = []
    all_labels: list[str] = []

    prev_last: str | None = block.get("_prev_last_screenshot")  # type: ignore[assignment]
    if prev_last:
        all_screenshots.append(prev_last)
        all_labels.append(_screenshot_label(prev_last))

    all_screenshots.extend(screenshots)
    all_labels.extend(_screenshot_label(f) for f in screenshots)

    # Build slide HTML
    slides_html: list[str] = []
    for i, label in enumerate(all_labels):
        active = ' data-active="true"' if i == 0 else ""
        light_src = f"light/{all_screenshots[i]}"
        dark_src = f"dark/{all_screenshots[i]}"

        slides_html.append(
            f'  <div class="guide-slide"{active}'
            f' data-light-src="{escape(light_src)}"'
            f' data-dark-src="{escape(dark_src)}"'
            f' data-label="{escape(label)}">'
            f'    <img class="guide-slide-img" src="" alt="{escape(label)}" loading="lazy">'
            f"  </div>"
        )

    slides = "\n".join(slides_html)
    total = len(all_screenshots)

    viewport: dict[str, int] = block.get("_viewport", {"width": 1280, "height": 800})  # type: ignore[assignment]
    vp_width = viewport.get("width", 1280)
    vp_height = viewport.get("height", 800)

    return (
        f'<div class="guide-slideshow" data-total="{total}"'
        f' data-width="{vp_width}" data-height="{vp_height}">\n'
        f'  <div class="guide-slides">\n{slides}\n  </div>\n'
        f'  <div class="guide-controls">\n'
        f'    <button class="guide-prev" aria-label="Previous step" disabled>&lsaquo;</button>\n'
        f'    <span class="guide-counter">1 / {total}</span>\n'
        f'    <span class="guide-label">{escape(all_labels[0]) if all_labels else ""}</span>\n'
        f'    <button class="guide-next" aria-label="Next step">&rsaquo;</button>\n'
        f"  </div>\n"
        f"</div>"
    )


def _render_placeholder(source: str, message: str) -> str:
    """Render a placeholder when screenshots aren't available."""
    return (
        f'<div class="guide-placeholder">\n'
        f"  <p><em>{escape(message)}</em></p>\n"
        f"  <details>\n"
        f"    <summary>Guide code</summary>\n"
        f"    <pre><code>{escape(source)}</code></pre>\n"
        f"  </details>\n"
        f"</div>"
    )


def format_guide(
    source: str,
    _language: str,
    _class_name: str,
    _options: dict[str, str],
    _md: object,
    **_kwargs: object,
) -> str:
    """Format a ```guide fence block as a screenshot slideshow.

    This function follows the pymdownx.superfences custom fence API:
        format(source, language, class_name, options, md, **kwargs) -> str

    Args:
        source: The content inside the fenced block.
        _language: The fence language identifier ("guide").
        _class_name: CSS class name from the fence config.
        _options: Fence options (unused).
        _md: The Markdown processor instance.
        **_kwargs: Additional keyword arguments.

    Returns:
        HTML string to replace the fenced block.

    """
    block = _find_block(source)

    if block is None:
        return _render_placeholder(source, "Run guide tests to generate screenshots")

    return _render_slideshow(block, source)

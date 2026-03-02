"""Custom fence formatter for ``guide`` code blocks.

Renders guide blocks as screenshot slideshows in documentation output.
Used by pymdownx.superfences as a custom fence format function.

Screenshots are loaded from manifest.json files produced by the guide
test suite (``tests/guides/test_guides.py``) or the CLI runner
(``tools/guide_runner``). Manifests are discovered by scanning the
docs directory on first use — no hook or build wrapper needed.

If no manifest exists (e.g., guide tests haven't been run yet),
the code block is rendered as a styled placeholder.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from xml.sax.saxutils import escape

_LOGGER = logging.getLogger(__name__)

_DOCS_DIR = Path(__file__).parent.parent / "docs"

# Lazy-loaded index: maps content_hash -> block data dict.
# Populated on first call to _find_block().
_block_index: dict[str, dict[str, object]] | None = None


def _load_manifests() -> dict[str, dict[str, object]]:
    """Scan docs/ for manifest.json files and index blocks by content hash."""
    index: dict[str, dict[str, object]] = {}

    for manifest_path in _DOCS_DIR.rglob("manifest.json"):
        try:
            with manifest_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            _LOGGER.debug("Skipping invalid manifest: %s", manifest_path)
            continue

        for block in data.get("blocks", []):
            if isinstance(block, dict) and "content_hash" in block:
                index[block["content_hash"]] = block

    _LOGGER.debug("Loaded %d guide blocks from manifests", len(index))
    return index


def _find_block(source: str) -> dict[str, object] | None:
    """Find the manifest block matching this source code by content hash."""
    global _block_index  # noqa: PLW0603
    if _block_index is None:
        _block_index = _load_manifests()

    content_hash = hashlib.sha256(source.strip().encode()).hexdigest()[:16]
    return _block_index.get(content_hash)


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
    """Render a screenshot slideshow for a guide block."""
    screenshots: list[str] = block.get("screenshots", [])  # type: ignore[assignment]

    if not screenshots:
        return _render_placeholder(source, "No screenshots captured for this block")

    labels = [_screenshot_label(f) for f in screenshots]

    # Build slide HTML
    slides_html: list[str] = []
    for i, label in enumerate(labels):
        active = ' data-active="true"' if i == 0 else ""
        light_src = f"light/{screenshots[i]}"
        dark_src = f"dark/{screenshots[i]}"

        slides_html.append(
            f'  <div class="guide-slide"{active}'
            f' data-light-src="{escape(light_src)}"'
            f' data-dark-src="{escape(dark_src)}"'
            f' data-label="{escape(label)}">'
            f'    <img class="guide-slide-img" src="" alt="{escape(label)}" loading="lazy">'
            f"  </div>"
        )

    slides = "\n".join(slides_html)
    total = len(screenshots)

    return (
        f'<div class="guide-slideshow" data-total="{total}">\n'
        f'  <div class="guide-slides">\n{slides}\n  </div>\n'
        f'  <div class="guide-controls">\n'
        f'    <button class="guide-prev" aria-label="Previous step" disabled>&lsaquo;</button>\n'
        f'    <span class="guide-counter">1 / {total}</span>\n'
        f'    <span class="guide-label">{escape(labels[0]) if labels else ""}</span>\n'
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

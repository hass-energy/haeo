"""Custom fence formatter for ``guide`` code blocks.

Renders guide blocks as screenshot slideshows in MkDocs output.
Used by pymdownx.superfences as a custom fence format function.

Screenshots are loaded from a pre-built manifest.json file
(produced by ``tools.guide_runner``) located in a sibling directory
named after the markdown file.

If no manifest exists (e.g., during development without running the guide),
the code block is rendered as a styled placeholder.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from xml.sax.saxutils import escape

_LOGGER = logging.getLogger(__name__)

# Module-level registry: maps markdown source paths to their manifest data.
# Populated by the mkdocs hook or build script before rendering.
_manifests: dict[str, dict[str, object]] = {}


def register_manifest(md_source_path: str, manifest_path: Path) -> None:
    """Register a manifest for a markdown source file.

    Called during docs build setup to make manifests available to the formatter.

    Args:
        md_source_path: Relative path of the markdown file (e.g., "user-guide/examples/sigenergy-system.md").
        manifest_path: Absolute path to the manifest.json file.

    """
    if manifest_path.exists():
        with manifest_path.open(encoding="utf-8") as f:
            _manifests[md_source_path] = json.load(f)
        _LOGGER.debug("Registered manifest for %s", md_source_path)
    else:
        _LOGGER.debug("No manifest found at %s", manifest_path)


def _find_block(source: str) -> dict[str, object] | None:
    """Find the manifest block matching this source code by content hash."""
    content_hash = hashlib.sha256(source.encode()).hexdigest()[:16]

    for manifest_data in _manifests.values():
        blocks = manifest_data.get("blocks", [])
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("content_hash") == content_hash:
                return block

    return None


def _screenshot_label(filename: str) -> str:
    """Derive a human-readable label from a screenshot filename.

    Transforms "045_add_battery.fill_Battery_Name.filled.png"
    into "Fill Battery Name".
    """
    # Strip numeric prefix and .png extension
    name = filename
    if name.endswith(".png"):
        name = name[:-4]
    # Remove leading NNN_ prefix
    parts = name.split("_", 1)
    if len(parts) > 1 and parts[0].isdigit():
        name = parts[1]

    # Split on dots to get hierarchy parts, take the meaningful ones
    dot_parts = name.split(".")
    # Skip the top-level step name (e.g., "add_battery") and take the rest
    if len(dot_parts) > 1:
        label_parts = dot_parts[1:]
    else:
        label_parts = dot_parts

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
    light_files: list[str] = block.get("light", [])  # type: ignore[assignment]
    dark_files: list[str] = block.get("dark", [])  # type: ignore[assignment]

    if not light_files and not dark_files:
        return _render_placeholder(source, "No screenshots captured for this block")

    # Use light files as the primary set for labels
    primary_files = light_files or dark_files
    labels = [_screenshot_label(f) for f in primary_files]

    # Build slide HTML
    slides_html: list[str] = []
    for i, label in enumerate(labels):
        active = ' data-active="true"' if i == 0 else ""
        light_src = f"light/{light_files[i]}" if i < len(light_files) else ""
        dark_src = f"dark/{dark_files[i]}" if i < len(dark_files) else ""

        slides_html.append(
            f'  <div class="guide-slide"{active}'
            f' data-light-src="{escape(light_src)}"'
            f' data-dark-src="{escape(dark_src)}"'
            f' data-label="{escape(label)}">'
            f'    <img class="guide-slide-img" src="" alt="{escape(label)}" loading="lazy">'
            f"  </div>"
        )

    slides = "\n".join(slides_html)
    total = len(primary_files)

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
    language: str,
    class_name: str,
    options: dict[str, str],
    md: object,
    **kwargs: object,
) -> str:
    """Format a ```guide fence block as a screenshot slideshow.

    This function follows the pymdownx.superfences custom fence API:
        format(source, language, class_name, options, md, **kwargs) -> str

    Args:
        source: The content inside the fenced block.
        language: The fence language identifier ("guide").
        class_name: CSS class name from the fence config.
        options: Fence options (unused).
        md: The Markdown processor instance.
        **kwargs: Additional keyword arguments.

    Returns:
        HTML string to replace the fenced block.

    """
    block = _find_block(source)

    if block is None:
        return _render_placeholder(source, "Run guide runner to generate screenshots")

    return _render_slideshow(block, source)

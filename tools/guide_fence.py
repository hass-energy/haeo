"""Custom fence formatter for ``guide`` code blocks.

Renders guide blocks as screenshot slideshows in documentation output.
Used by pymdownx.superfences as a custom fence format function.

Screenshots are loaded from manifest.json files produced by the guide
test suite (``tests/guides/test_guides.py``) or the CLI runner
(``tools/guide_runner``). Manifests are discovered by scanning the
docs directory on first use — no hook or build wrapper needed.

If no manifest exists (e.g., guide tests haven't been run yet),
the code block is rendered as a styled placeholder.

Cross-block continuity: a block's screenshot slideshow starts with the
last screenshot of the closest earlier block that has one, providing visual
continuity between slideshows.

Figures, such as rendered cards saved as SVG, stand on their own. They are
shown after the block's screenshots, with arrows to flick between them when
a block saves more than one, and never carry over into other blocks.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import re
from xml.sax.saxutils import escape

from tools.guide_hashing import compute_content_hash, compute_page_hash, extract_sources

_LOGGER = logging.getLogger(__name__)

_DOCS_DIR = Path(__file__).parent.parent / "docs"

_FIGURE_SUFFIX = ".svg"
_DEFAULT_VIEWPORT = {"width": 1280, "height": 800}
_SVG_SIZE = re.compile(r'<svg[^>]*\swidth="(\d+)"[^>]*\sheight="(\d+)"')

_manifest_cache: dict[str, dict[str, object]] | None = None
_manifest_mtimes: dict[Path, float] = {}


def _load_manifests() -> dict[str, dict[str, object]]:
    """Scan docs/ for manifest.json files and index blocks by content hash.

    Enriches each block with ``_prev_last_screenshot`` — the last screenshot
    of the closest earlier block in the same page manifest that has one,
    ``_viewport`` — the screenshot viewport dimensions from the manifest,
    and ``_figure_sizes`` — the size of each of the block's figures.
    """
    index: dict[str, dict[str, object]] = {}
    _manifest_mtimes.clear()

    for manifest_path in _DOCS_DIR.rglob("manifest.json"):
        try:
            with manifest_path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            _LOGGER.debug("Skipping invalid manifest: %s", manifest_path)
            continue

        _manifest_mtimes[manifest_path] = manifest_path.stat().st_mtime

        viewport = data.get("viewport", _DEFAULT_VIEWPORT)
        blocks = data.get("blocks", [])
        prev_last: str | None = None
        for block in blocks:
            if not isinstance(block, dict) or "content_hash" not in block:
                continue

            screenshots, figures = _split_captures(block.get("screenshots", []))
            block["_prev_last_screenshot"] = prev_last
            block["_viewport"] = viewport
            block["_figure_sizes"] = [_figure_size(manifest_path.parent / "light" / name) for name in figures]
            if screenshots:
                prev_last = screenshots[-1]

            content_hash = block["content_hash"]
            if content_hash in index:
                _LOGGER.warning(
                    "Duplicate guide block hash %s in %s",
                    content_hash,
                    manifest_path,
                )
            index[content_hash] = block

    _LOGGER.debug("Loaded %d guide blocks from manifests", len(index))
    return index


def _split_captures(captures: list[str]) -> tuple[list[str], list[str]]:
    """Split a block's captures into its screenshots and its figures."""
    figures = [name for name in captures if name.endswith(_FIGURE_SUFFIX)]
    return [name for name in captures if not name.endswith(_FIGURE_SUFFIX)], figures


def _figure_size(path: Path) -> dict[str, int]:
    """Return the width and height a figure declares, or the screenshot viewport when it cannot be read."""
    try:
        match = _SVG_SIZE.search(path.read_text(encoding="utf-8")[:2000])
    except OSError:
        return dict(_DEFAULT_VIEWPORT)
    return {"width": int(match[1]), "height": int(match[2])} if match else dict(_DEFAULT_VIEWPORT)


def _manifests_changed() -> bool:
    """Check whether any cached manifest file has been modified.

    Only checks mtimes of previously discovered manifests (no filesystem
    traversal). New manifests added after the initial scan won't be
    detected until the cache is next cleared — this is fine for mkdocs
    build where all manifests exist at build start.
    """
    return any(not p.exists() or p.stat().st_mtime != mtime for p, mtime in _manifest_mtimes.items())


def _get_page_hash(md: object) -> str:
    """Get or compute the page hash for this Markdown processor instance.

    Each page gets a fresh ``Markdown`` instance. On first call, the
    page hash is computed from all guide block sources in ``md.lines``
    and cached on the instance for subsequent blocks on the same page.
    """
    cached: str | None = getattr(md, "_guide_page_hash", None)
    if cached is not None:
        return cached

    lines: list[str] = getattr(md, "lines", [])
    markdown = "\n".join(lines)
    sources = extract_sources(markdown)
    page_hash = compute_page_hash(sources)

    md._guide_page_hash = page_hash  # type: ignore[attr-defined]  # noqa: SLF001 (stashing state on mkdocs Markdown instance, no public API available)
    return page_hash


def _find_block(source: str, page_hash: str) -> dict[str, object] | None:
    """Find the manifest block matching this source code by content hash."""
    global _manifest_cache  # noqa: PLW0603 (module-level cache requires global reassignment)
    if _manifest_cache is None or _manifests_changed():
        _manifest_cache = _load_manifests()
    content_hash = compute_content_hash(page_hash, source)
    return _manifest_cache.get(content_hash)


def _screenshot_label(filename: str) -> str:
    """Derive a human-readable label from a screenshot filename.

    Transforms "045_add_battery.fill_Battery_Name.filled.png"
    into "Fill Battery Name".
    """
    # Strip numeric prefix and extension
    name = filename.removesuffix(".png").removesuffix(_FIGURE_SUFFIX)
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


def _render_carousel(
    captures: list[str], labels: list[str], *, sizes: list[dict[str, int]], class_name: str, item: str
) -> str:
    """Render captures with prev/next controls, or alone when there is only one.

    Each slide carries its own size, so the frame keeps the shape of the slide on show.
    """
    slides_html: list[str] = []
    for i, (capture, label, size) in enumerate(zip(captures, labels, sizes, strict=True)):
        active = ' data-active="true"' if i == 0 else ""
        light_src = f"light/{capture}"
        dark_src = f"dark/{capture}"

        slides_html.append(
            f'  <div class="guide-slide"{active}'
            f' data-light-src="{escape(light_src)}"'
            f' data-dark-src="{escape(dark_src)}"'
            f' data-label="{escape(label)}"'
            f' data-width="{size["width"]}" data-height="{size["height"]}">'
            f'    <img class="guide-slide-img" src="" alt="{escape(label)}" loading="lazy">'
            f"  </div>"
        )

    slides = "\n".join(slides_html)
    total = len(captures)
    if total > 1:
        controls = (
            f'  <div class="guide-controls">\n'
            f'    <button class="guide-prev" aria-label="Previous {item}" disabled>&lsaquo;</button>\n'
            f'    <span class="guide-counter">1 / {total}</span>\n'
            f'    <span class="guide-label">{escape(labels[0])}</span>\n'
            f'    <button class="guide-next" aria-label="Next {item}">&rsaquo;</button>\n'
            f"  </div>\n"
        )
    else:
        controls = (
            f'  <div class="guide-controls">\n    <span class="guide-label">{escape(labels[0])}</span>\n  </div>\n'
        )

    return (
        f'<div class="{class_name}" data-total="{total}"'
        f' data-width="{sizes[0]["width"]}" data-height="{sizes[0]["height"]}">\n'
        f'  <div class="guide-slides">\n{slides}\n  </div>\n'
        f"{controls}"
        f"</div>"
    )


def _render_block(block: dict[str, object], source: str) -> str:
    """Render a guide block's screenshot slideshow followed by its figures.

    The slideshow starts with the last screenshot of the closest earlier
    block that has one, for visual continuity between slideshows.
    """
    screenshots, figures = _split_captures(block.get("screenshots", []))  # type: ignore[arg-type]

    if not screenshots and not figures:
        return _render_placeholder(source, "No screenshots captured for this block")

    parts: list[str] = []
    if screenshots:
        prev_last: str | None = block.get("_prev_last_screenshot")  # type: ignore[assignment]
        slides = [prev_last, *screenshots] if prev_last else screenshots
        viewport: dict[str, int] = block.get("_viewport", _DEFAULT_VIEWPORT)  # type: ignore[assignment]
        parts.append(
            _render_carousel(
                slides,
                [_screenshot_label(name) for name in slides],
                sizes=[viewport] * len(slides),
                class_name="guide-slideshow",
                item="step",
            )
        )
    if figures:
        figure_sizes: list[dict[str, int]] = block["_figure_sizes"]  # type: ignore[assignment]
        parts.append(
            _render_carousel(
                figures,
                [_screenshot_label(name) for name in figures],
                sizes=figure_sizes,
                class_name="guide-slideshow guide-figures",
                item="figure",
            )
        )
    return "\n".join(parts)


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
    page_hash = _get_page_hash(_md)
    block = _find_block(source, page_hash)

    if block is None:
        return _render_placeholder(source, "Run guide tests to generate screenshots")

    return _render_block(block, source)


def format_guide_setup(
    _source: str,
    _language: str,
    _class_name: str,
    _options: dict[str, str],
    _md: object,
    **_kwargs: object,
) -> str:
    """Format a ```guide-setup fence block as hidden content.

    Setup blocks run prerequisite guide steps during test execution
    but are not rendered in the documentation output.
    """
    return ""

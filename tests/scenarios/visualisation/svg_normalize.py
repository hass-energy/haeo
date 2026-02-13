"""SVG normalization helpers for deterministic scenario artifacts."""

from pathlib import Path
import re

_CLIP_PATH_ID_PATTERN = re.compile(r'(<clipPath\b[^>]*\bid=")([^"]+)(")', re.IGNORECASE)


def normalize_clip_path_ids(svg_content: str) -> str:
    """Normalize clipPath IDs and url() references to deterministic names.

    Matplotlib may produce different backend-generated clipPath IDs across
    machines. This function rewrites clipPath IDs in first-seen order to
    canonical names (``clipPath1``, ``clipPath2``, ...), then updates all
    matching ``url(#...)`` references.
    """

    id_map: dict[str, str] = {}

    def _replace_clip_id(match: re.Match[str]) -> str:
        old_id = match.group(2)
        if old_id not in id_map:
            id_map[old_id] = f"clipPath{len(id_map) + 1}"
        return f"{match.group(1)}{id_map[old_id]}{match.group(3)}"

    normalized = _CLIP_PATH_ID_PATTERN.sub(_replace_clip_id, svg_content)

    for old_id, new_id in id_map.items():
        normalized = normalized.replace(f"url(#{old_id})", f"url(#{new_id})")

    return normalized


def normalize_svg_file_clip_paths(svg_path: Path) -> None:
    """Normalize clipPath IDs in an SVG file in place."""
    original = svg_path.read_text(encoding="utf-8")
    normalized = normalize_clip_path_ids(original)
    if normalized != original:
        svg_path.write_text(normalized, encoding="utf-8")

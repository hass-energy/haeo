"""Shared hashing utilities for guide blocks.

Used by both the guide runner (to write manifests) and the guide fence
formatter (to look up blocks). Keeping the algorithms in one place
ensures the hashes always match.

Content hashes are page-scoped: ``sha256(page_hash + ":" + source)``.
This ensures identical code blocks (e.g., ``verify_setup(page)``) on
different pages produce different hashes, avoiding cross-page collisions.
"""

from __future__ import annotations

import hashlib
import re

_GUIDE_BLOCK_RE = re.compile(
    r"^```guide(?:-setup)?\s*\n(?P<source>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


def compute_page_hash(sources: list[str]) -> str:
    """Compute a combined hash from all guide block sources on a page.

    Includes both setup and non-setup blocks since changes to either
    affect the screenshots.
    """
    combined = "\n---\n".join(sources)
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def compute_content_hash(page_hash: str, source: str) -> str:
    """Compute a page-scoped content hash for a single guide block.

    Including ``page_hash`` ensures identical source code on different
    pages (e.g., ``verify_setup(page)``) produces different hashes.
    """
    combined = f"{page_hash}:{source.strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def extract_sources(markdown: str) -> list[str]:
    """Extract guide block sources from raw markdown text.

    Returns sources in document order, including both setup and
    non-setup blocks.
    """
    return [m.group("source") for m in _GUIDE_BLOCK_RE.finditer(markdown)]

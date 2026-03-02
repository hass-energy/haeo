"""MkDocs hook that registers guide manifests for the custom fence formatter.

This hook scans the docs directory for manifest.json files produced by
the guide runner and registers them with the fence formatter so that
```guide blocks can be rendered as screenshot slideshows.

Configure in mkdocs.yml:
    hooks:
      - tools/mkdocs_guide_hook.py
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from tools.guide_fence import register_manifest

_LOGGER = logging.getLogger(__name__)


def on_config(config: dict[str, Any]) -> dict[str, Any]:
    """Register guide manifests when MkDocs config is loaded.

    Scans the docs directory for manifest.json files in subdirectories
    that correspond to markdown files with guide blocks.
    """
    docs_dir = Path(config["docs_dir"])

    # Find all manifest.json files under docs/
    for manifest_path in docs_dir.rglob("manifest.json"):
        # The manifest directory name matches the markdown file stem
        # e.g., docs/user-guide/examples/sigenergy-system/manifest.json
        #   → docs/user-guide/examples/sigenergy-system.md
        manifest_dir = manifest_path.parent
        md_file = manifest_dir.with_suffix(".md")

        if md_file.exists():
            # Relative path from docs_dir
            rel_path = md_file.relative_to(docs_dir).as_posix()
            register_manifest(rel_path, manifest_path)
            _LOGGER.info("Registered guide manifest for %s", rel_path)

    return config

"""Check audit coverage for collected pytest nodeids."""

from __future__ import annotations

import logging
from pathlib import Path
import re

ROOT = Path("/Users/trenthouliston/Code/gaeo")
NODEIDS_PATH = ROOT / ".plans/pytest-collect-nodeids.txt"
AUDIT_ROOT = ROOT / "test_audit"

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Report missing audit files for collected pytest nodeids."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    nodeids: list[str] = []
    with NODEIDS_PATH.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith("tests/"):
                continue
            nodeids.append(line)

    param_map: dict[str, dict[str, object]] = {}
    for nodeid in nodeids:
        parts = nodeid.split("::")
        file_path = parts[0]
        class_parts = parts[1:-1]
        func_part = parts[-1]
        match = re.match(r"(?P<name>[^\[]+)(?:\[(?P<param>.*)\])?$", func_part)
        func_name = match.group("name") if match else func_part
        base_key = "::".join([file_path, *class_parts, func_name])
        param_map.setdefault(
            base_key,
            {
                "file_path": file_path,
                "class_parts": class_parts,
                "func_name": func_name,
            },
        )

    missing: list[str] = []
    for entry in param_map.values():
        file_path = ROOT / str(entry["file_path"])
        rel = file_path.relative_to(ROOT / "tests")
        audit_dir = AUDIT_ROOT / rel.parent / rel.stem
        class_label = "__".join(entry["class_parts"]) if entry["class_parts"] else ""
        file_base = "__".join(part for part in [class_label, entry["func_name"]] if part)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", file_base)
        audit_path = audit_dir / f"{safe_name}.md"
        if not audit_path.exists():
            missing.append(str(audit_path))

    LOGGER.info("Base tests: %s", len(param_map))
    LOGGER.info("Missing audit files: %s", len(missing))
    for path in missing[:10]:
        LOGGER.info(path)


if __name__ == "__main__":
    main()

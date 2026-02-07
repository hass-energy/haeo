"""Generate markdown audit files for collected pytest tests and fixtures."""

from __future__ import annotations

import logging
from pathlib import Path
import re

ROOT = Path("/Users/trenthouliston/Code/gaeo")
NODEIDS_PATH = ROOT / ".plans/pytest-collect-nodeids.txt"
AUDIT_ROOT = ROOT / "test_audit"

LOGGER = logging.getLogger(__name__)


def load_nodeids() -> list[str]:
    """Load pytest nodeids from the collection output file."""
    nodeids: list[str] = []
    with NODEIDS_PATH.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            if not line.startswith("tests/"):
                continue
            nodeids.append(line)
    return nodeids


def build_param_map(nodeids: list[str]) -> dict[str, dict[str, object]]:
    """Group nodeids by base test and track parameters."""
    param_map: dict[str, dict[str, object]] = {}
    for nodeid in nodeids:
        parts = nodeid.split("::")
        file_path = parts[0]
        class_parts = parts[1:-1]
        func_part = parts[-1]
        match = re.match(r"(?P<name>[^\[]+)(?:\[(?P<param>.*)\])?$", func_part)
        if match:
            func_name = match.group("name")
            param_id = match.group("param")
        else:
            func_name = func_part
            param_id = None

        base_key = "::".join([file_path, *class_parts, func_name])
        entry = param_map.setdefault(
            base_key,
            {
                "nodeid": base_key,
                "file_path": file_path,
                "class_parts": class_parts,
                "func_name": func_name,
                "params": [],
            },
        )
        if param_id is not None:
            entry["params"].append(param_id)
    return param_map


def write_audit_file(
    audit_path: Path,
    nodeid: str,
    file_path: str,
    class_parts: list[str],
    func_name: str,
    params: list[str],
) -> None:
    """Write a single audit file using the standard template."""
    per_param_review = bool(params)
    param_entries = "\n".join(
        f'    - id: "{param}"\n'
        "      reviewed: false\n"
        "      decision: undecided\n"
        '      behavior: ""\n'
        '      redundancy: ""'
        for param in params
    )
    if not param_entries:
        param_entries = "    []"

    frontmatter = f"""---
status:
  reviewed: false
  decision: undecided
  behavior_documented: false
  redundancy_noted: false
parameterized:
  per_parameter_review: {str(per_param_review).lower()}
  cases:
{param_entries}
meta:
  nodeid: \"{nodeid}\"
  source_file: \"{file_path}\"
  test_class: \"{"::".join(class_parts)}\"
  test_function: \"{func_name}\"
  fixtures: []
  markers: []
notes:
  behavior: \"\"
  redundancy: \"\"
  decision_rationale: \"\"
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions
"""

    audit_path.write_text(frontmatter, encoding="utf-8")


def write_conftest_audit(audit_path: Path, conftest_path: Path) -> None:
    """Write a fixture audit file for a conftest module."""
    frontmatter = f"""---
status:
  reviewed: false
  decision: undecided
  behavior_documented: false
  redundancy_noted: false
meta:
  source_file: \"{conftest_path.as_posix()}\"
  fixtures: []
notes:
  behavior: \"\"
  redundancy: \"\"
  decision_rationale: \"\"
---

# Fixture summary

# Usage and scope

# Redundancy / overlap

# Decision rationale

# Next actions
"""
    audit_path.write_text(frontmatter, encoding="utf-8")


def main() -> None:
    """Generate audit files for all collected tests and conftest fixtures."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    nodeids = load_nodeids()
    param_map = build_param_map(nodeids)

    created = 0
    tests_root = ROOT / "tests"

    for entry in param_map.values():
        file_path = ROOT / entry["file_path"]
        try:
            rel = file_path.relative_to(tests_root)
        except ValueError:
            continue

        class_parts = entry["class_parts"]
        func_name = entry["func_name"]
        params = entry["params"]

        audit_dir = AUDIT_ROOT / rel.parent / rel.stem
        audit_dir.mkdir(parents=True, exist_ok=True)

        class_label = "__".join(class_parts) if class_parts else ""
        file_base = "__".join(part for part in [class_label, func_name] if part)
        safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", file_base)
        audit_path = audit_dir / f"{safe_name}.md"

        if audit_path.exists():
            continue

        write_audit_file(
            audit_path,
            entry["nodeid"],
            entry["file_path"],
            class_parts,
            func_name,
            params,
        )
        created += 1

    for conftest in ROOT.glob("tests/**/conftest.py"):
        rel = conftest.relative_to(tests_root)
        audit_dir = AUDIT_ROOT / rel.parent
        audit_dir.mkdir(parents=True, exist_ok=True)
        audit_path = audit_dir / "conftest.md"
        if audit_path.exists():
            continue
        write_conftest_audit(audit_path, conftest)
        created += 1

    LOGGER.info("Created %s audit files.", created)


if __name__ == "__main__":
    main()

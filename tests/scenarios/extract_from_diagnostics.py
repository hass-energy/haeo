#!/usr/bin/env python3
"""Extract scenario test files from HAEO diagnostics JSON.

Usage:
    python extract_from_diagnostics.py diagnostics.json output_dir/

This will create:
    output_dir/scenario.json (single file in diagnostic format)
"""

import json
from pathlib import Path
import sys


def extract_scenario(diagnostics_path: Path, output_dir: Path) -> None:
    """Extract scenario file from diagnostics JSON."""
    with diagnostics_path.open() as f:
        diagnostics = json.load(f)

    # Verify the new format with config, inputs, outputs, environment keys
    if not all(key in diagnostics for key in ("config", "inputs", "environment")):
        print("Error: diagnostics file does not contain expected keys (config, inputs, environment)")
        print("This might be from an older version of HAEO diagnostics")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as single scenario.json file with sorted keys
    # Keys are already in the right order: config, environment, inputs, outputs
    scenario_path = output_dir / "scenario.json"
    with scenario_path.open("w") as f:
        json.dump(diagnostics, f, indent=2, sort_keys=False)

    print(f"✓ Saved scenario to {scenario_path}")
    print(f"  - Config with {len(diagnostics['config'].get('participants', {}))} participants")
    print(f"  - {len(diagnostics['inputs'])} input states")
    print(f"  - {len(diagnostics.get('outputs', []))} output states")
    ha_version = diagnostics["environment"].get("ha_version")
    timestamp = diagnostics["environment"].get("timestamp")
    print(f"  - Environment: {ha_version} @ {timestamp}")

    print("\nScenario file created successfully!")
    print("\nTo run this scenario:")
    print(f"  uv run pytest tests/scenarios/ -m scenario -k {output_dir.name}")


def main() -> None:
    """Execute main extraction logic."""
    if len(sys.argv) != 3:
        print("Usage: python extract_from_diagnostics.py diagnostics.json output_dir/")
        sys.exit(1)

    diagnostics_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])

    if not diagnostics_path.exists():
        print(f"Error: diagnostics file not found: {diagnostics_path}")
        sys.exit(1)

    extract_scenario(diagnostics_path, output_dir)


if __name__ == "__main__":
    main()

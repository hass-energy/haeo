#!/usr/bin/env python3
"""Extract scenario test files from HAEO diagnostics JSON.

Usage:
    python extract_from_diagnostics.py diagnostics.json output_dir/

This will create:
    output_dir/config.json
    output_dir/states.json
"""

import json
import sys
from pathlib import Path


def extract_scenario(diagnostics_path: Path, output_dir: Path) -> None:
    """Extract scenario files from diagnostics JSON."""
    with diagnostics_path.open() as f:
        diagnostics = json.load(f)

    # Verify the new format with config, inputs, outputs, environment keys
    if not all(key in diagnostics for key in ("config", "inputs", "environment")):
        print("Error: diagnostics file does not contain expected keys (config, inputs, environment)")
        print("This might be from an older version of HAEO diagnostics")
        sys.exit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save config
    config_path = output_dir / "config.json"
    with config_path.open("w") as f:
        json.dump(diagnostics["config"], f, indent=2)
    print(f"✓ Saved config to {config_path}")

    # Save input states
    states_path = output_dir / "states.json"
    with states_path.open("w") as f:
        json.dump(diagnostics["inputs"], f, indent=2)
    print(f"✓ Saved {len(diagnostics['inputs'])} input states to {states_path}")

    # Optionally save output states for reference
    if diagnostics.get("outputs"):
        output_states_path = output_dir / "output_states.json"
        with output_states_path.open("w") as f:
            json.dump(diagnostics["outputs"], f, indent=2)
        print(f"✓ Saved {len(diagnostics['outputs'])} output states to {output_states_path}")
        print("  (output_states.json is for reference only, not used by tests)")

    # Save environment info for debugging
    env_path = output_dir / "environment.json"
    with env_path.open("w") as f:
        json.dump(diagnostics["environment"], f, indent=2)
    print(f"✓ Saved environment info to {env_path}")

    print("\nScenario files created successfully!")
    print(f"\nTo run this scenario:")
    print(f"  uv run pytest tests/scenarios/ -m scenario -k {output_dir.name}")


def main() -> None:
    """Main entry point."""
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

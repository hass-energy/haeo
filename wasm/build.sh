#!/usr/bin/env bash
set -euo pipefail

# Build haeo-core pure-Python wheel for WASM usage.
# Output goes to wasm/dist/ (gitignored).
#
# The highspy WASM wheel must be built separately using pyodide-build
# (see README.md for instructions) and placed in wasm/dist/.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"

# Read version from pyproject.toml
VERSION=$(python3 -c "
import re, pathlib
text = pathlib.Path('$REPO_ROOT/pyproject.toml').read_text()
m = re.search(r'^version\s*=\s*\"([^\"]+)\"', text, re.MULTILINE)
print(m.group(1))
")
echo "Building haeo-core wheel (version: $VERSION)"

# Clean previous output
rm -rf "$DIST_DIR/haeo_core-"*.whl
mkdir -p "$DIST_DIR"

# Create a temporary package directory for the core-only wheel
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Copy core source
cp -r "$REPO_ROOT/custom_components" "$TEMP_DIR/"

# Remove HA-dependent modules (keep only core/)
find "$TEMP_DIR/custom_components/haeo" -maxdepth 1 -type f ! -name '__init__.py' -delete
for dir in "$TEMP_DIR/custom_components/haeo"/*/; do
    basename=$(basename "$dir")
    if [[ "$basename" != "core" && "$basename" != "__pycache__" ]]; then
        rm -rf "$dir"
    fi
done
rm -rf "$TEMP_DIR/custom_components/haeo"/__pycache__

# Write a minimal __init__.py for the haeo package
echo '"""HAEO core - standalone optimization engine."""' > "$TEMP_DIR/custom_components/haeo/__init__.py"
echo "" > "$TEMP_DIR/custom_components/__init__.py"

# Write pyproject.toml with current version
cat > "$TEMP_DIR/pyproject.toml" <<EOF
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "haeo-core"
version = "$VERSION"
requires-python = ">=3.11"
dependencies = ["numpy", "highspy"]

[tool.setuptools.packages.find]
include = ["custom_components*"]
EOF

# Build the wheel
uv run --with build python3 -m build --wheel "$TEMP_DIR" --outdir "$DIST_DIR"

echo ""
echo "Built: $(ls "$DIST_DIR"/haeo_core-*.whl)"
echo ""
echo "To use in Storybook, copy the wheel and highspy WASM wheel to the staticDirs path."

"""Tests for import boundaries in the core package."""

from pathlib import Path


def test_core_package_has_no_homeassistant_imports() -> None:
    """`core/` modules must not import Home Assistant packages."""
    core_root = Path(__file__).resolve().parents[2] / "custom_components" / "haeo" / "core"

    for path in core_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "from homeassistant" not in source
        assert "import homeassistant" not in source

"""Tests for the documentation assembly helpers."""

from __future__ import annotations

from pathlib import Path

from tools import assemble_docs
from tools.assemble_docs import Release, build_version_entries, docs_asset_name, parse_tag, write_redirect


def test_parse_tag_stable() -> None:
    """A stable ``vX.Y.Z`` tag parses with the stable sentinel rc rank."""
    result = parse_tag("v0.3.3")
    assert result is not None
    assert result.tag == "v0.3.3"
    assert result.version == "0.3.3"
    assert result.is_rc is False
    assert result.sort_key[:3] == (0, 3, 3)


def test_parse_tag_rc() -> None:
    """A release-candidate tag is flagged and sorts before the matching stable."""
    rc = parse_tag("v0.4.0rc1")
    stable = parse_tag("v0.4.0")
    assert rc is not None
    assert stable is not None
    assert rc.is_rc is True
    assert rc.version == "0.4.0rc1"
    assert rc.sort_key < stable.sort_key


def test_parse_tag_rejects_non_standard() -> None:
    """Tags that don't match the release regex (e.g. alphas) are ignored."""
    assert parse_tag("v0.1.0-alpha") is None
    assert parse_tag("main") is None
    assert parse_tag("") is None


def test_parse_tag_sort_order() -> None:
    """Sorting newest-first groups RCs before their stable and higher X.Y.Z first."""
    tags = ["v0.1.0", "v0.2.0", "v0.3.0rc1", "v0.3.0", "v0.3.3", "v0.4.0rc1"]
    parsed = [p for p in (parse_tag(t) for t in tags) if p is not None]
    parsed.sort(key=lambda r: r.sort_key, reverse=True)
    assert [r.tag for r in parsed] == [
        "v0.4.0rc1",
        "v0.3.3",
        "v0.3.0",
        "v0.3.0rc1",
        "v0.2.0",
        "v0.1.0",
    ]


def _release(tag: str, *, is_rc: bool) -> Release:
    """Minimal Release factory for tests."""
    return Release(tag=tag, version=tag[1:], sort_key=(0, 0, 0, 0), is_rc=is_rc)


def test_build_version_entries_sets_latest_and_dev_aliases() -> None:
    """versions.json places main first with ``dev`` alias; newest non-rc gets ``latest``."""
    rc = _release("v0.4.0rc1", is_rc=True)
    stable = _release("v0.3.3", is_rc=False)
    older = _release("v0.2.0", is_rc=False)
    entries = build_version_entries([rc, stable, older], stable, "main", "dev", "latest")
    assert entries[0] == {"version": "main", "title": "main", "aliases": ["dev"]}
    versions = [entry["version"] for entry in entries]
    assert versions == ["main", "0.4.0rc1", "0.3.3", "0.2.0"]
    aliases_by_version = {entry["version"]: entry["aliases"] for entry in entries}
    assert aliases_by_version["0.3.3"] == ["latest"]
    assert aliases_by_version["0.4.0rc1"] == []
    assert aliases_by_version["0.2.0"] == []


def test_build_version_entries_no_stable() -> None:
    """When no non-rc release exists, no version gets the ``latest`` alias."""
    rc = _release("v0.4.0rc1", is_rc=True)
    entries = build_version_entries([rc], None, "main", "dev", "latest")
    for entry in entries:
        assert "latest" not in entry["aliases"]


def test_write_redirect(tmp_path: Path) -> None:
    """The redirect file meta-refreshes to the given target."""
    path = tmp_path / "index.html"
    write_redirect(path, "latest")
    content = path.read_text(encoding="utf-8")
    assert '<meta http-equiv="refresh" content="0; url=./latest/">' in content
    assert '<link rel="canonical" href="./latest/">' in content


def test_docs_asset_name() -> None:
    """Release docs assets are namespaced by tag so each release gets its own filename."""
    assert docs_asset_name("v0.3.3") == "docs-v0.3.3.zip"
    assert docs_asset_name("v0.4.0rc1") == "docs-v0.4.0rc1.zip"


def test_module_constants() -> None:
    """Sanity-check module-level constants relied on by workflows."""
    assert assemble_docs.DEFAULT_CNAME == "haeo.io"

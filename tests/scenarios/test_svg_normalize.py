"""Tests for deterministic SVG normalization helpers."""

from tests.scenarios.visualisation.svg_normalize import normalize_clip_path_ids


def test_normalize_clip_path_ids_rewrites_ids_and_references() -> None:
    """ClipPath IDs and their url() references are rewritten consistently."""
    svg = """
<svg>
  <defs>
    <clipPath id="pab60df210f"><rect x="0" y="0" width="10" height="10"/></clipPath>
    <clipPath id="p3b01cfcd6b"><rect x="1" y="1" width="8" height="8"/></clipPath>
  </defs>
  <g clip-path="url(#pab60df210f)"><path d="M 0 0"/></g>
  <g style="clip-path:url(#p3b01cfcd6b)"><path d="M 1 1"/></g>
</svg>
"""
    normalized = normalize_clip_path_ids(svg)

    assert 'clipPath id="clipPath1"' in normalized
    assert 'clipPath id="clipPath2"' in normalized
    assert "url(#clipPath1)" in normalized
    assert "url(#clipPath2)" in normalized
    assert "pab60df210f" not in normalized
    assert "p3b01cfcd6b" not in normalized


def test_normalize_clip_path_ids_is_idempotent() -> None:
    """Repeated normalization yields identical output."""
    svg = """
<svg>
  <defs>
    <clipPath id="pabc"><rect x="0" y="0" width="1" height="1"/></clipPath>
  </defs>
  <g clip-path="url(#pabc)"><path d="M 0 0"/></g>
</svg>
"""
    first_pass = normalize_clip_path_ids(svg)
    second_pass = normalize_clip_path_ids(first_pass)

    assert first_pass == second_pass

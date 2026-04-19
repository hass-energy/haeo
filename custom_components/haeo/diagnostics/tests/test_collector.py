"""Unit tests for :mod:`custom_components.haeo.diagnostics.collector`.

These focus on the serialization helpers rather than the async HA collection
path — the goal is to guarantee the JSON that hits disk contains only plain
primitives, since scenario fixtures consume it as pure JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
import json
import re
from types import MappingProxyType
from typing import Any

import pytest

from custom_components.haeo.diagnostics.collector import (
    DIAGNOSTICS_SCHEMA_VERSION,
    DiagnosticsInfo,
    DiagnosticsResult,
    EnvironmentInfo,
    _jsonify,
)


class _Color(StrEnum):
    """StrEnum fixture for Enum-unwrapping tests."""

    RED = "red"
    BLUE = "blue"


class _Priority(IntEnum):
    """IntEnum fixture for Enum-unwrapping tests."""

    LOW = 1
    HIGH = 9


class _Mode(Enum):
    """Plain Enum fixture (value is a string)."""

    ON = "on"
    OFF = "off"


@dataclass(frozen=True)
class _Point:
    """Dataclass fixture for asdict flattening."""

    x: int
    y: int


def _is_plain_json(value: Any) -> bool:
    """Return ``True`` iff *value* is a tree of JSON primitives / dict / list."""
    if isinstance(value, dict):
        return all(isinstance(k, str) and _is_plain_json(v) for k, v in value.items())
    if isinstance(value, list):
        return all(_is_plain_json(v) for v in value)
    return isinstance(value, (str, int, float, bool)) or value is None


def test_jsonify_passes_through_plain_dict() -> None:
    """A dict of primitives is returned unchanged."""
    data = {"a": 1, "b": "two", "c": [1, 2, 3], "d": None, "e": True}
    assert _jsonify(data) == data


def test_jsonify_unwraps_mappingproxytype_recursively() -> None:
    """Nested ``MappingProxyType`` is flattened to plain ``dict``."""
    inner = MappingProxyType({"name": "Battery", "value": 42})
    outer = MappingProxyType({"participants": {"bat": inner}})

    result = _jsonify(outer)

    assert isinstance(result, dict)
    assert not isinstance(result, MappingProxyType)
    assert isinstance(result["participants"], dict)
    assert isinstance(result["participants"]["bat"], dict)
    assert result == {"participants": {"bat": {"name": "Battery", "value": 42}}}


def test_jsonify_unwraps_enum_stringly_and_numerically() -> None:
    """StrEnum / IntEnum / Enum members are replaced by their ``.value``."""
    assert _jsonify(_Color.RED) == "red"
    assert _jsonify(_Priority.HIGH) == 9
    assert _jsonify(_Mode.ON) == "on"
    assert _jsonify({"k": [_Color.BLUE, _Priority.LOW]}) == {"k": ["blue", 1]}


def test_jsonify_converts_frozenset_tuple_and_set_to_list() -> None:
    """Non-JSON iterables become lists (order-insensitive for sets)."""
    result = _jsonify({"frozen": frozenset({2, 1, 3}), "tup": (1, 2), "plain_set": {4}})
    assert sorted(result["frozen"]) == [1, 2, 3]
    assert result["tup"] == [1, 2]
    assert sorted(result["plain_set"]) == [4]


def test_jsonify_serializes_datetime_to_iso() -> None:
    """``datetime`` / ``date`` / ``timedelta`` serialize to ISO / seconds."""
    dt = datetime(2026, 4, 19, 12, 30, 45, tzinfo=UTC)
    assert _jsonify(dt) == "2026-04-19T12:30:45+00:00"
    assert _jsonify(date(2026, 4, 19)) == "2026-04-19"
    assert _jsonify(timedelta(minutes=5)) == 300.0


def test_jsonify_decimal_becomes_string() -> None:
    """``Decimal`` survives as a string (exact value on round-trip)."""
    assert _jsonify(Decimal("1.234")) == "1.234"
    assert Decimal(_jsonify(Decimal("0.1"))) == Decimal("0.1")


def test_jsonify_dataclass_is_recursively_flattened() -> None:
    """Dataclasses are flattened via ``asdict`` and further jsonified."""
    p = _Point(1, 2)
    assert _jsonify(p) == {"x": 1, "y": 2}
    assert _jsonify({"points": [p, _Point(3, 4)]}) == {"points": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]}


def test_jsonify_bytes_becomes_utf8_string() -> None:
    """UTF-8 ``bytes`` decode to ``str``."""
    assert _jsonify(b"hello") == "hello"


def test_jsonify_output_is_pure_json() -> None:
    """End-to-end: a gnarly mix of types round-trips through ``json.dumps``."""
    data = {
        "proxy": MappingProxyType({"enum": _Color.RED, "when": datetime(2026, 1, 1, tzinfo=UTC)}),
        "tags": frozenset({"a", "b"}),
        "price": Decimal("3.14"),
        "point": _Point(7, 8),
        "nested": MappingProxyType(
            {
                "tier": _Priority.HIGH,
                "children": [MappingProxyType({"t": _Mode.OFF})],
            },
        ),
    }

    plain = _jsonify(data)

    assert _is_plain_json(plain), f"Non-JSON leaf remaining: {plain!r}"
    dumped = json.dumps(plain)
    # No HA ExtendedJSONEncoder fallback stubs should appear anywhere.
    assert "mappingproxy(" not in dumped
    assert "<class " not in dumped
    assert "__type" not in dumped
    assert json.loads(dumped) == plain


def test_diagnostics_result_includes_schema_version_and_timestamp() -> None:
    """``DiagnosticsResult.to_dict`` emits ``schema_version`` + clean JSON."""
    ts = "2026-04-19T12:00:00+00:00"
    result = DiagnosticsResult(
        config={"participants": {}},
        environment=EnvironmentInfo(
            ha_version="2026.1.1",
            haeo_version="0.4.0",
            timestamp=ts,
            timezone="UTC",
        ),
        inputs=[],
        info=DiagnosticsInfo(
            diagnostic_request_time=ts,
            diagnostic_target_time=None,
            optimization_start_time=ts,
            optimization_end_time=ts,
            horizon_start=ts,
        ),
        outputs=None,
        missing_entity_ids=(),
    )

    out = result.to_dict()

    assert out["schema_version"] == DIAGNOSTICS_SCHEMA_VERSION
    assert out["environment"]["timestamp"] == ts
    dumped = json.dumps(out)
    assert not re.search(r"mappingproxy\(|<class ", dumped)


@pytest.mark.parametrize(
    "value",
    [42, 3.14, "hello", True, False, None, [], {}],
)
def test_jsonify_leaves_primitives_alone(value: Any) -> None:
    """JSON primitives and empty containers pass through untouched."""
    assert _jsonify(value) == value

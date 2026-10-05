"""Tests for reading when an availability source was last off."""

import pytest

from conftest import FakeEntityState
from custom_components.haeo.core.data.loader.last_off import (
    LAST_OFF_ATTRIBUTE,
    is_off_state,
    last_off_field,
    last_off_time,
    read_last_off,
)
from custom_components.haeo.core.schema.elements.ev import CONF_CONNECTED, CONF_CONNECTED_LAST_OFF


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("off", True),
        ("False", True),
        ("0", True),
        ("on", False),
        ("true", False),
        ("1", False),
        ("unavailable", False),
        ("unknown", False),
    ],
)
def test_is_off_state(raw: str, *, expected: bool) -> None:
    """Off, false, and zero read as off; on and unparseable states do not."""
    assert is_off_state(raw) is expected


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        pytest.param([("off", 100.0), ("on", 200.0)], 200.0, id="plugged_in_after_off"),
        pytest.param(
            [("off", 100.0), ("on", 200.0), ("off", 300.0), ("on", 400.0)],
            400.0,
            id="latest_off_wins",
        ),
        pytest.param([("off", 100.0), ("unavailable", 150.0), ("on", 200.0)], 150.0, id="off_ends_at_restart"),
        pytest.param([("on", 100.0), ("unavailable", 150.0), ("on", 200.0)], None, id="restart_is_not_off"),
        pytest.param([("on", 100.0), ("off", 200.0)], None, id="still_off"),
        pytest.param([("on", 100.0)], None, id="never_off"),
        pytest.param([], None, id="no_history"),
    ],
)
def test_last_off_time(changes: list[tuple[str, float]], expected: float | None) -> None:
    """The last off time is when the latest off reading gave way to another state."""
    assert last_off_time(changes) == expected


@pytest.mark.parametrize(
    ("attributes", "expected"),
    [
        pytest.param({LAST_OFF_ATTRIBUTE: 123.5}, 123.5, id="float"),
        pytest.param({LAST_OFF_ATTRIBUTE: 123}, 123.0, id="int"),
        pytest.param({LAST_OFF_ATTRIBUTE: True}, None, id="bool"),
        pytest.param({LAST_OFF_ATTRIBUTE: "123"}, None, id="string"),
        pytest.param({}, None, id="missing"),
    ],
)
def test_read_last_off(attributes: dict[str, object], expected: float | None) -> None:
    """Only a numeric injected attribute reads as a last off time."""
    assert read_last_off(FakeEntityState("binary_sensor.plug", "on", attributes)) == expected


def test_read_last_off_without_state() -> None:
    """A missing state has no last off time."""
    assert read_last_off(None) is None


def test_ev_last_off_key_matches_loader_convention() -> None:
    """The EV schema's last off key is the one the loader writes for the connected field."""
    assert last_off_field(CONF_CONNECTED) == CONF_CONNECTED_LAST_OFF

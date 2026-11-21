"""Tests for the selector behind a connection's path."""

import pytest
import voluptuous as vol

from custom_components.haeo.core.schema import as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.flows.connection_path_selector import (
    CONNECTION_PATH_STRINGS,
    CONNECTION_PATH_TRANSLATION_KEY,
    ConnectionPathSelector,
    ConnectionPathSelectorConfig,
)
from custom_components.haeo.flows.input_selector import InputSelectorConfig

LIMIT_INPUT: InputSelectorConfig = {
    "kinds": ["entity", "constant"],
    "value_type": "number",
    "domains": ["sensor"],
    "forecasts": {},
    "entities": ["sensor.limit"],
    "min": 0.0,
    "max": 100.0,
}
CONFIG: ConnectionPathSelectorConfig = {
    "participants": [{"name": "Inverter", "element_type": "inverter"}, {"name": "Bus", "element_type": "node"}],
    "segment_types": {"power_limit": {"field": "max_power", "input": LIMIT_INPUT}},
}


def _path(segments: list[object], *, source: object = "Inverter", target: object = "Bus") -> dict[str, object]:
    return {"source": source, "target": target, "segments": segments}


def test_selector_returns_the_endpoints_and_each_segment_s_validated_input() -> None:
    """The endpoints come back by name and each segment with its input as stored, in order."""
    selector = ConnectionPathSelector(CONFIG)

    result = selector(
        _path(
            [
                {"segment_type": "power_limit", "max_power": {"type": "constant", "value": "5"}},
                {"segment_type": "power_limit", "max_power": {"type": "entity", "value": ["sensor.limit"]}},
                {"segment_type": "power_limit", "max_power": {"type": "entity", "value": []}},
            ]
        )
    )

    assert result == _path(
        [
            {"segment_type": "power_limit", "max_power": as_constant_value(5.0)},
            {"segment_type": "power_limit", "max_power": as_entity_value(["sensor.limit"])},
            {"segment_type": "power_limit", "max_power": as_none_value()},
        ]
    )


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(_path([], source="Elsewhere"), id="unknown_source"),
        pytest.param(_path([], target=None), id="missing_target"),
        pytest.param(_path([{"segment_type": "pricing", "price": as_constant_value(1.0)}]), id="unknown_segment_type"),
        pytest.param(
            _path([{"segment_type": "power_limit", "max_power": as_constant_value(500.0)}]), id="input_out_of_range"
        ),
        pytest.param(
            _path([{"segment_type": "power_limit", "max_power": as_entity_value(["sensor.other"])}]),
            id="entity_not_offered",
        ),
        pytest.param({"source": "Inverter", "target": "Bus", "segments": "none"}, id="segments_not_a_list"),
        pytest.param(_path(["not a segment"]), id="segment_not_a_mapping"),
        pytest.param("Inverter", id="not_a_path"),
    ],
)
def test_selector_rejects_what_the_path_does_not_offer(path: object) -> None:
    """Endpoints, segment types and inputs the path does not offer are rejected."""
    with pytest.raises(vol.Invalid):
        ConnectionPathSelector(CONFIG)(path)


def test_selector_lists_its_strings() -> None:
    """The element's labels are listed with the placeholders it fills in."""
    assert dict(ConnectionPathSelector.translation_strings()) == {
        ("selector", CONNECTION_PATH_TRANSLATION_KEY, "options", key): placeholders
        for key, placeholders in CONNECTION_PATH_STRINGS.items()
    }

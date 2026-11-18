"""Tests for the v1.7 schema migration."""

import pytest

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.migrations.v1_7 import migrate_element_config

SENSORS = {"House": "sensor.house_power", "Solar": "sensor.solar_power"}


def _buffer(participants: dict[str, object]) -> dict[str, object]:
    return {CONF_ELEMENT_TYPE: ElementType.BUFFER, CONF_NAME: "Backup", "kind": "reserve", "participants": participants}


@pytest.mark.parametrize(
    ("participants", "expected"),
    [
        pytest.param(
            {"loads": ["House"], "generation": ["Solar"], "storage": ["Battery"]},
            {
                "loads": as_entity_value(["sensor.house_power"]),
                "generation": as_entity_value(["sensor.solar_power"]),
                "storage": ["Battery"],
            },
            id="elements_named_by_their_sensors",
        ),
        pytest.param(
            {"loads": ["House", "Pool pump"], "storage": ["Battery"]},
            {"loads": {**as_entity_value(["sensor.house_power"]), "elements": ["Pool pump"]}, "storage": ["Battery"]},
            id="element_without_a_sensor_named_directly",
        ),
        pytest.param(
            {"loads": [], "generation": [], "storage": ["Battery"]},
            {"storage": ["Battery"]},
            id="empty_lists_are_dropped",
        ),
        pytest.param(
            {"loads": as_entity_value(["sensor.load_p90"]), "generation": ["Solar"], "storage": ["Battery"]},
            {
                "loads": as_entity_value(["sensor.load_p90"]),
                "generation": as_entity_value(["sensor.solar_power"]),
                "storage": ["Battery"],
            },
            id="sensor_fields_are_kept",
        ),
    ],
)
def test_buffer_names_its_loads_and_generation_by_sensor(
    participants: dict[str, object], expected: dict[str, object]
) -> None:
    """Each element a buffer lists is named by its sensor, or directly when it has none."""
    migrated = migrate_element_config(_buffer(participants), SENSORS)

    assert migrated is not None
    assert migrated["participants"] == expected
    assert migrated[CONF_NAME] == "Backup"


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({CONF_ELEMENT_TYPE: ElementType.LOAD, CONF_NAME: "House"}, id="not_a_buffer"),
        pytest.param(_buffer({"storage": ["Battery"]}), id="buffer_without_loads_or_generation"),
        pytest.param(
            _buffer({"loads": as_entity_value(["sensor.house_power"]), "storage": ["Battery"]}),
            id="buffer_already_naming_sensors",
        ),
    ],
)
def test_configs_that_list_no_elements_are_left_alone(config: dict[str, object]) -> None:
    """Only a buffer that lists its loads or generation by name changes."""
    assert migrate_element_config(config, SENSORS) is None

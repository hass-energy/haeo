"""Test hub options flow for network configuration."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_INTEGRATION_TYPE,
    CONF_RECORD_FORECASTS,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
    OUTPUT_NAME_HORIZON,
)
from custom_components.haeo.core.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON,
    CONF_NAME,
    DEFAULT_DEBOUNCE_SECONDS,
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
)
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.horizon_value import HorizonValue, as_horizon_preset_value
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON

type FlowResultDict = dict[str, object]

HORIZON_ENTITY_ID = "sensor.horizon_source"

ADVANCED_INPUT = {CONF_DEBOUNCE_SECONDS: 5, CONF_ADVANCED_MODE: True, CONF_RECORD_FORECASTS: True}


def _hub_entry(hass: HomeAssistant, horizon: HorizonValue) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {CONF_NAME: "Test Hub", CONF_HORIZON: horizon},
            HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS},
        },
    )
    entry.add_to_hass(hass)
    return entry


def _set_haeo_forecast_sensor(hass: HomeAssistant, entity_id: str = HORIZON_ENTITY_ID) -> None:
    """Set a sensor reporting a HAEO-format forecast usable as a horizon."""
    hass.states.async_set(
        entity_id,
        "0",
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": "2025-01-01T12:00:00+00:00", "value": 0},
                {"time": "2025-01-01T12:30:00+00:00", "value": 0},
            ],
        },
    )


def _common_schema(result: FlowResultDict) -> vol.Schema:
    data_schema = result["data_schema"]
    assert isinstance(data_schema, vol.Schema)
    section_map = {marker.schema: section for marker, section in data_schema.schema.items()}
    return section_map[HUB_SECTION_COMMON].schema


def _flow_id(result: FlowResultDict) -> str:
    flow_id = result["flow_id"]
    assert isinstance(flow_id, str)
    return flow_id


async def _submit(hass: HomeAssistant, entry: MockConfigEntry, horizon: object) -> FlowResultDict:
    result: FlowResultDict = await hass.config_entries.options.async_init(entry.entry_id)  # type: ignore[assignment]  # HA returns ConfigFlowResult; tests index as dict[str, object]
    return await hass.config_entries.options.async_configure(  # type: ignore[return-value]  # HA returns ConfigFlowResult; tests index as dict[str, object]
        _flow_id(result),
        user_input={HUB_SECTION_COMMON: {CONF_HORIZON: horizon}, HUB_SECTION_ADVANCED: ADVANCED_INPUT},
    )


@pytest.mark.parametrize(
    ("horizon", "expected_default"),
    [
        pytest.param(as_horizon_preset_value(HORIZON_PRESET_3_DAYS), HORIZON_PRESET_3_DAYS, id="preset"),
        pytest.param(as_entity_value([HORIZON_ENTITY_ID]), HORIZON_ENTITY_ID, id="entity"),
    ],
)
async def test_options_flow_defaults_to_current_horizon(
    hass: HomeAssistant, horizon: HorizonValue, expected_default: str
) -> None:
    """The options form defaults the horizon to the hub's current horizon."""
    entry = _hub_entry(hass, horizon)

    result: FlowResultDict = await hass.config_entries.options.async_init(entry.entry_id)  # type: ignore[assignment]  # HA returns ConfigFlowResult; tests index as dict[str, object]

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"
    schema_keys = {vol_key.schema: vol_key for vol_key in _common_schema(result).schema}
    assert schema_keys[CONF_HORIZON].default() == expected_default


@pytest.mark.parametrize(
    ("horizon_input", "expected"),
    [
        pytest.param(
            {"active_choice": "preset", "preset": HORIZON_PRESET_3_DAYS},
            as_horizon_preset_value(HORIZON_PRESET_3_DAYS),
            id="preset",
        ),
        pytest.param(
            {"active_choice": "entity", "entity": HORIZON_ENTITY_ID},
            as_entity_value([HORIZON_ENTITY_ID]),
            id="entity",
        ),
    ],
)
async def test_options_flow_saves_horizon_and_advanced_settings(
    hass: HomeAssistant, horizon_input: object, expected: HorizonValue
) -> None:
    """Saving the options stores the chosen horizon and the advanced settings."""
    _set_haeo_forecast_sensor(hass)
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))

    result = await _submit(hass, entry, horizon_input)

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[HUB_SECTION_COMMON] == {CONF_NAME: "Test Hub", CONF_HORIZON: expected}
    assert entry.data[HUB_SECTION_ADVANCED] == {CONF_DEBOUNCE_SECONDS: 5, CONF_ADVANCED_MODE: True}
    assert entry.data[CONF_RECORD_FORECASTS] is True


async def test_options_flow_rejects_invalid_horizon_entity(hass: HomeAssistant) -> None:
    """A horizon entity without a HAEO forecast shows the form again and keeps the old horizon."""
    hass.states.async_set(HORIZON_ENTITY_ID, "12")
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))

    result = await _submit(hass, entry, {"active_choice": "entity", "entity": HORIZON_ENTITY_ID})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HORIZON: "horizon_entity_invalid"}
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON] == as_horizon_preset_value(HORIZON_PRESET_5_DAYS)


@pytest.mark.parametrize("unique_key", [OUTPUT_NAME_HORIZON, "battery_power"], ids=["horizon_sensor", "output_sensor"])
async def test_options_flow_rejects_this_hubs_sensors(hass: HomeAssistant, unique_key: str) -> None:
    """A sensor belonging to the hub cannot set its horizon, because it is computed on that horizon."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))
    own_sensor = (
        er.async_get(hass)
        .async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_{unique_key}", config_entry=entry)
        .entity_id
    )
    _set_haeo_forecast_sensor(hass, own_sensor)

    result = await _submit(hass, entry, {"active_choice": "entity", "entity": own_sensor})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HORIZON: "horizon_entity_from_this_hub"}


async def test_options_flow_accepts_another_hubs_horizon_sensor(hass: HomeAssistant) -> None:
    """Another hub's horizon sensor, whose forecast points carry only times, can set the horizon."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))
    hass.states.async_set(
        HORIZON_ENTITY_ID,
        "2025-01-01T12:00:00+00:00",
        {"forecast": [{"time": "2025-01-01T12:00:00+00:00"}, {"time": "2025-01-01T13:00:00+00:00"}]},
    )

    result = await _submit(hass, entry, {"active_choice": "entity", "entity": HORIZON_ENTITY_ID})

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON] == as_entity_value([HORIZON_ENTITY_ID])

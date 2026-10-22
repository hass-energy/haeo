"""Test the hub settings form shared by the options flow and the reconfigure flow."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

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
    CONF_RELAX_INFEASIBLE,
    DEFAULT_DEBOUNCE_SECONDS,
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
)
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.horizon_value import HorizonValue, as_horizon_preset_value
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON

type FlowResultDict = dict[str, object]

HORIZON_ENTITY_ID = "sensor.horizon_source"

ADVANCED_INPUT = {
    CONF_DEBOUNCE_SECONDS: 5,
    CONF_ADVANCED_MODE: True,
    CONF_RELAX_INFEASIBLE: True,
    CONF_RECORD_FORECASTS: True,
}


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


@dataclass(frozen=True)
class HubSettingsFlow:
    """A flow that edits the hub settings: how to start it and how it finishes."""

    start: Callable[[HomeAssistant, MockConfigEntry], Awaitable[FlowResultDict]]
    configure: Callable[[HomeAssistant, str, dict[str, object]], Awaitable[FlowResultDict]]
    step_id: str
    finished: FlowResultType


async def _start_options(hass: HomeAssistant, entry: MockConfigEntry) -> FlowResultDict:
    return await hass.config_entries.options.async_init(entry.entry_id)  # type: ignore[return-value]  # HA returns ConfigFlowResult; tests index as dict[str, object]


async def _configure_options(hass: HomeAssistant, flow_id: str, user_input: dict[str, object]) -> FlowResultDict:
    return await hass.config_entries.options.async_configure(flow_id, user_input=user_input)  # type: ignore[return-value]  # HA returns ConfigFlowResult; tests index as dict[str, object]


async def _start_reconfigure(hass: HomeAssistant, entry: MockConfigEntry) -> FlowResultDict:
    return await entry.start_reconfigure_flow(hass)  # type: ignore[return-value]  # HA returns ConfigFlowResult; tests index as dict[str, object]


async def _configure_reconfigure(hass: HomeAssistant, flow_id: str, user_input: dict[str, object]) -> FlowResultDict:
    return await hass.config_entries.flow.async_configure(flow_id, user_input=user_input)  # type: ignore[return-value]  # HA returns ConfigFlowResult; tests index as dict[str, object]


@pytest.fixture(
    params=[
        pytest.param(
            HubSettingsFlow(_start_options, _configure_options, "init", FlowResultType.CREATE_ENTRY), id="options"
        ),
        pytest.param(
            HubSettingsFlow(_start_reconfigure, _configure_reconfigure, "reconfigure", FlowResultType.ABORT),
            id="reconfigure",
        ),
    ]
)
def settings_flow(request: pytest.FixtureRequest) -> HubSettingsFlow:
    """Each flow that edits the hub settings."""
    flow: HubSettingsFlow = request.param
    return flow


async def _submit(
    hass: HomeAssistant, flow: HubSettingsFlow, entry: MockConfigEntry, horizon: object
) -> FlowResultDict:
    result = await flow.start(hass, entry)
    return await flow.configure(
        hass,
        _flow_id(result),
        {HUB_SECTION_COMMON: {CONF_HORIZON: horizon}, HUB_SECTION_ADVANCED: ADVANCED_INPUT},
    )


@pytest.mark.parametrize(
    ("horizon", "expected_default"),
    [
        pytest.param(as_horizon_preset_value(HORIZON_PRESET_3_DAYS), HORIZON_PRESET_3_DAYS, id="preset"),
        pytest.param(as_entity_value([HORIZON_ENTITY_ID]), HORIZON_ENTITY_ID, id="entity"),
    ],
)
async def test_hub_settings_default_to_current_horizon(
    hass: HomeAssistant, settings_flow: HubSettingsFlow, horizon: HorizonValue, expected_default: str
) -> None:
    """The hub settings form defaults the horizon to the hub's current horizon."""
    entry = _hub_entry(hass, horizon)

    result = await settings_flow.start(hass, entry)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == settings_flow.step_id
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
async def test_hub_settings_save_horizon_and_advanced_settings(
    hass: HomeAssistant, settings_flow: HubSettingsFlow, horizon_input: object, expected: HorizonValue
) -> None:
    """Saving the hub settings stores the chosen horizon and the advanced settings."""
    _set_haeo_forecast_sensor(hass)
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))

    result = await _submit(hass, settings_flow, entry, horizon_input)

    assert result["type"] == settings_flow.finished
    assert entry.data[HUB_SECTION_COMMON] == {CONF_NAME: "Test Hub", CONF_HORIZON: expected}
    assert entry.data[HUB_SECTION_ADVANCED] == {
        CONF_DEBOUNCE_SECONDS: 5,
        CONF_ADVANCED_MODE: True,
        CONF_RELAX_INFEASIBLE: True,
    }
    assert entry.data[CONF_RECORD_FORECASTS] is True


async def test_hub_settings_reject_invalid_horizon_entity(hass: HomeAssistant, settings_flow: HubSettingsFlow) -> None:
    """A horizon entity without a HAEO forecast shows the form again and keeps the old horizon."""
    hass.states.async_set(HORIZON_ENTITY_ID, "12")
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))

    result = await _submit(hass, settings_flow, entry, {"active_choice": "entity", "entity": HORIZON_ENTITY_ID})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HORIZON: "horizon_entity_invalid"}
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON] == as_horizon_preset_value(HORIZON_PRESET_5_DAYS)


@pytest.mark.parametrize("unique_key", [OUTPUT_NAME_HORIZON, "battery_power"], ids=["horizon_sensor", "output_sensor"])
async def test_hub_settings_reject_this_hubs_sensors(
    hass: HomeAssistant, settings_flow: HubSettingsFlow, unique_key: str
) -> None:
    """A sensor belonging to the hub cannot set its horizon, because it is computed on that horizon."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))
    own_sensor = (
        er.async_get(hass)
        .async_get_or_create("sensor", DOMAIN, f"{entry.entry_id}_{unique_key}", config_entry=entry)
        .entity_id
    )
    _set_haeo_forecast_sensor(hass, own_sensor)

    result = await _submit(hass, settings_flow, entry, {"active_choice": "entity", "entity": own_sensor})

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_HORIZON: "horizon_entity_from_this_hub"}


async def test_hub_settings_accept_another_hubs_horizon_sensor(
    hass: HomeAssistant, settings_flow: HubSettingsFlow
) -> None:
    """Another hub's horizon sensor, whose forecast points carry only times, can set the horizon."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))
    hass.states.async_set(
        HORIZON_ENTITY_ID,
        "2025-01-01T12:00:00+00:00",
        {"forecast": [{"time": "2025-01-01T12:00:00+00:00"}, {"time": "2025-01-01T13:00:00+00:00"}]},
    )

    result = await _submit(hass, settings_flow, entry, {"active_choice": "entity", "entity": HORIZON_ENTITY_ID})

    assert result["type"] == settings_flow.finished
    assert entry.data[HUB_SECTION_COMMON][CONF_HORIZON] == as_entity_value([HORIZON_ENTITY_ID])


async def test_reconfigure_flow_finishes_with_reconfigure_successful(hass: HomeAssistant) -> None:
    """The reconfigure flow aborts with the reconfigure_successful reason once the settings are saved."""
    entry = _hub_entry(hass, as_horizon_preset_value(HORIZON_PRESET_5_DAYS))
    flow = HubSettingsFlow(_start_reconfigure, _configure_reconfigure, "reconfigure", FlowResultType.ABORT)

    result = await _submit(hass, flow, entry, {"active_choice": "preset", "preset": HORIZON_PRESET_3_DAYS})

    assert result["reason"] == "reconfigure_successful"

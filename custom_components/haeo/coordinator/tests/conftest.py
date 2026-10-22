"""Fixtures shared by the coordinator tests."""

from collections.abc import Generator
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any  # noqa: TID251  # Mock-typed test doubles (MagicMock spec=)
from unittest.mock import MagicMock, patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, ELEMENT_TYPE_NETWORK, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_NAME,
    DEFAULT_DEBOUNCE_SECONDS,
    HORIZON_PRESET_2_DAYS,
)
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_LIMIT_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_ADVANCED,
    SECTION_LIMITS,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS
from custom_components.haeo.core.schema.elements.grid import (
    CONF_MAX_POWER_SOURCE_TARGET as CONF_GRID_MAX_POWER_SOURCE_TARGET,
)
from custom_components.haeo.core.schema.elements.grid import (
    CONF_MAX_POWER_TARGET_SOURCE as CONF_GRID_MAX_POWER_TARGET_SOURCE,
)
from custom_components.haeo.core.schema.elements.grid import CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            HUB_SECTION_COMMON: {
                CONF_NAME: "Power Network",
                CONF_HORIZON: as_horizon_preset_value(HORIZON_PRESET_2_DAYS),
            },
            HUB_SECTION_ADVANCED: {CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS},
        },
        entry_id="hub_entry_id",
    )
    entry.add_to_hass(hass)
    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_NAME: "System", CONF_ELEMENT_TYPE: ELEMENT_TYPE_NETWORK}),
            subentry_type=ELEMENT_TYPE_NETWORK,
            title="System",
            unique_id=None,
        ),
    )
    return entry


@pytest.fixture
def mock_battery_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock battery subentry."""
    # Set up required sensors
    hass.states.async_set("sensor.battery_capacity", "10000", {"unit_of_measurement": UnitOfEnergy.WATT_HOUR})
    hass.states.async_set("sensor.battery_soc", "50.0")

    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.BATTERY,
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: as_connection_target("DC Bus"),
                SECTION_STORAGE: {
                    CONF_CAPACITY: as_entity_value(["sensor.battery_capacity"]),
                    CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                },
                SECTION_LIMITS: {
                    CONF_MIN_CHARGE_PERCENTAGE: as_constant_value(20.0),
                    CONF_MAX_CHARGE_PERCENTAGE: as_constant_value(80.0),
                },
                SECTION_POWER_LIMITS: {
                    CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                    CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
                },
                SECTION_PRICING: {
                    CONF_SALVAGE_VALUE: as_constant_value(0.0),
                },
                SECTION_EFFICIENCY: {
                    CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(95.0),
                    CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(95.0),
                },
                SECTION_ADVANCED: {
                    CONF_CHARGE_LIMIT_COST: as_constant_value(100.0),
                },
            }
        ),
        subentry_type=ElementType.BATTERY,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_grid_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock grid subentry."""
    hass.states.async_set("sensor.import_price", "0.30")
    hass.states.async_set("sensor.export_price", "0.05")

    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.GRID,
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: as_connection_target("AC Bus"),
                SECTION_PRICING: {
                    CONF_PRICE_SOURCE_TARGET: as_entity_value(["sensor.import_price"]),
                    CONF_PRICE_TARGET_SOURCE: as_entity_value(["sensor.export_price"]),
                },
                SECTION_POWER_LIMITS: {
                    CONF_GRID_MAX_POWER_SOURCE_TARGET: as_constant_value(10000),
                    CONF_GRID_MAX_POWER_TARGET_SOURCE: as_constant_value(5000),
                },
            }
        ),
        subentry_type=ElementType.GRID,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture
def mock_connection_subentry(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> ConfigSubentry:
    """Create a mock connection subentry."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ElementType.CONNECTION,
                CONF_NAME: "Battery to Grid",
                SECTION_ENDPOINTS: {
                    CONF_SOURCE: "Test Battery",
                    CONF_TARGET: "Test Grid",
                },
                SECTION_POWER_LIMITS: {},
                SECTION_PRICING: {},
                SECTION_EFFICIENCY: {},
            }
        ),
        subentry_type=ElementType.CONNECTION,
        title="Battery to Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(mock_hub_entry, subentry)
    return subentry


@pytest.fixture(autouse=True)
def patch_state_change_listener() -> Generator[MagicMock]:
    """Patch state change listener registration for tests."""
    with patch(
        "custom_components.haeo.coordinator.coordinator.async_track_state_change_event", return_value=lambda: None
    ) as mock_track:
        yield mock_track


@pytest.fixture
def mock_runtime_data(hass: HomeAssistant, mock_hub_entry: MockConfigEntry) -> HaeoRuntimeData:
    """Create mock runtime data with horizon manager and input entities.

    The horizon_manager is a MagicMock - use mock_horizon() to access mock methods.
    """
    # Avoid circular import with entities and horizon modules
    from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch  # noqa: PLC0415
    from custom_components.haeo.horizon import HorizonManager  # noqa: PLC0415

    # Create mock horizon manager (typed as HorizonManager but is MagicMock at runtime)
    mock_horizon: Any = MagicMock(spec=HorizonManager)
    mock_horizon.get_forecast_timestamps.return_value = (1000.0, 2000.0, 3000.0)
    mock_horizon.current_start_time = datetime.fromtimestamp(1000.0, tz=UTC)
    mock_horizon.subscribe.return_value = MagicMock()  # Unsubscribe function

    # Create mock auto-optimize switch (default to on)
    mock_auto_optimize_switch: Any = MagicMock(spec=AutoOptimizeSwitch)
    mock_auto_optimize_switch.is_on = True
    mock_auto_optimize_switch.entity_id = "switch.haeo_auto_optimize"

    # Create runtime data
    runtime_data = HaeoRuntimeData(
        horizon_manager=mock_horizon,
        auto_optimize_switch=mock_auto_optimize_switch,
    )

    # Store on config entry
    mock_hub_entry.runtime_data = runtime_data

    return runtime_data

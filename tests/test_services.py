"""Tests for HAEO service actions."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import async_setup
from custom_components.haeo.const import (
    CONF_INTEGRATION_TYPE,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)


@pytest.fixture
def mock_hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mock hub config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Network",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_hub_entry",
        title="Test HAEO Hub",
    )
    entry.add_to_hass(hass)
    return entry


async def test_async_setup_registers_service(hass: HomeAssistant) -> None:
    """Test that async_setup registers the save_diagnostics service."""
    result = await async_setup(hass, {})

    assert result is True
    assert hass.services.has_service(DOMAIN, "save_diagnostics")


async def test_save_diagnostics_service_success(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    tmp_path: Path,
) -> None:
    """Test save_diagnostics service writes file successfully."""
    # Set up the service
    await async_setup(hass, {})

    # Mock the entry state as loaded
    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    mock_hub_entry.runtime_data = None

    # Mock the diagnostics function
    mock_diagnostics = {
        "config": {"participants": {}},
        "environment": {"ha_version": "2024.1.0"},
        "inputs": [],
        "outputs": {},
    }

    # Mock config path to use tmp_path
    hass.config.config_dir = str(tmp_path)

    with patch(
        "custom_components.haeo.diagnostics.async_get_config_entry_diagnostics",
        new_callable=AsyncMock,
        return_value=mock_diagnostics,
    ):
        # Call the service
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    # Verify a file was created
    files = list(tmp_path.glob("haeo_diagnostics_*.json"))
    assert len(files) == 1

    # Verify file content matches Home Assistant's full diagnostics format
    with files[0].open() as f:
        saved_data = json.load(f)

    # Check that all expected top-level keys are present
    assert "home_assistant" in saved_data
    assert "custom_components" in saved_data
    assert "integration_manifest" in saved_data
    assert "setup_times" in saved_data
    assert "data" in saved_data

    # Verify the actual diagnostics data is in the "data" key
    assert saved_data["data"] == mock_diagnostics


async def test_save_diagnostics_service_entry_not_found(hass: HomeAssistant) -> None:
    """Test save_diagnostics raises error when config entry not found."""
    # Set up the service
    await async_setup(hass, {})

    # Call the service with non-existent entry ID
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": "non_existent_entry"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_not_found"


async def test_save_diagnostics_service_wrong_domain(hass: HomeAssistant) -> None:
    """Test save_diagnostics raises error when config entry is not HAEO."""
    # Set up the service
    await async_setup(hass, {})

    # Create a config entry for a different domain
    other_entry = MockConfigEntry(
        domain="other_integration",
        data={},
        entry_id="other_entry_id",
    )
    other_entry.add_to_hass(hass)

    # Call the service with wrong domain entry
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": other_entry.entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_wrong_domain"


async def test_save_diagnostics_service_entry_not_loaded(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Test save_diagnostics raises error when config entry not loaded."""
    # Set up the service
    await async_setup(hass, {})

    # Entry is NOT_LOADED by default (not explicitly set to LOADED)
    # Ensure it's in a non-loaded state
    mock_hub_entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)

    # Call the service with unloaded entry
    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_not_loaded"


async def test_save_diagnostics_filename_format(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    tmp_path: Path,
) -> None:
    """Test save_diagnostics creates file with correct naming format."""
    # Set up the service
    await async_setup(hass, {})

    # Mock the entry state as loaded
    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    mock_hub_entry.runtime_data = None

    # Mock config path
    hass.config.config_dir = str(tmp_path)

    with patch(
        "custom_components.haeo.diagnostics.async_get_config_entry_diagnostics",
        new_callable=AsyncMock,
        return_value={"config": {}, "environment": {}, "inputs": [], "outputs": {}},
    ):
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    # Verify filename format: haeo_diagnostics_<timestamp>.json
    files = list(tmp_path.glob("haeo_diagnostics_*.json"))
    assert len(files) == 1

    filename = files[0].name
    assert filename.startswith("haeo_diagnostics_")
    assert filename.endswith(".json")

    # Verify timestamp format in filename (YYYY-MM-DD_HHMMSS.microseconds)
    timestamp_part = filename.replace("haeo_diagnostics_", "").replace(".json", "")
    # Format: 2026-01-19_155018.452421 (27 chars: 10 date + 1 underscore + 6 time + 1 dot + 6 microseconds)
    assert len(timestamp_part) == 24
    assert timestamp_part[4] == "-"  # Year-month separator
    assert timestamp_part[7] == "-"  # Month-day separator
    assert timestamp_part[10] == "_"  # Date/time separator
    assert "." in timestamp_part  # Microseconds separator

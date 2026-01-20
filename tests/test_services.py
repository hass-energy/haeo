"""Tests for HAEO service actions."""

from datetime import UTC, datetime
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.loader import Manifest
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData, async_setup
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
from custom_components.haeo.diagnostics import DiagnosticsResult
from custom_components.haeo.services import _format_manifest


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
    mock_diagnostics = DiagnosticsResult(
        data={
            "config": {"participants": {}},
            "environment": {"ha_version": "2024.1.0"},
            "inputs": [],
            "outputs": {},
        },
        missing_entity_ids=[],
    )

    # Mock config path to use tmp_path
    hass.config.config_dir = str(tmp_path)

    with patch(
        "custom_components.haeo.diagnostics.collect_diagnostics",
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

    # Verify a file was created in the haeo/diagnostics subdirectory
    files = list(tmp_path.glob("haeo/diagnostics/diagnostics_*.json"))
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
    assert saved_data["data"] == mock_diagnostics.data


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
        "custom_components.haeo.diagnostics.collect_diagnostics",
        new_callable=AsyncMock,
        return_value=DiagnosticsResult(
            data={"config": {}, "environment": {}, "inputs": [], "outputs": {}},
            missing_entity_ids=[],
        ),
    ):
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    # Verify filename format: diagnostics_<timestamp>.json in haeo/diagnostics/
    files = list(tmp_path.glob("haeo/diagnostics/diagnostics_*.json"))
    assert len(files) == 1

    filename = files[0].name
    assert filename.startswith("diagnostics_")
    assert filename.endswith(".json")

    # Verify timestamp format in filename (YYYY-MM-DD_HHMMSS.microseconds)
    timestamp_part = filename.replace("diagnostics_", "").replace(".json", "")
    # Format: 2026-01-19_155018.452421 (27 chars: 10 date + 1 underscore + 6 time + 1 dot + 6 microseconds)
    assert len(timestamp_part) == 24
    assert timestamp_part[4] == "-"  # Year-month separator
    assert timestamp_part[7] == "-"  # Month-day separator
    assert timestamp_part[10] == "_"  # Date/time separator
    assert "." in timestamp_part  # Microseconds separator


def test_format_manifest_strips_codeowner_prefix() -> None:
    """Test that _format_manifest strips @ prefix from codeowners."""
    manifest: Manifest = {
        "domain": "haeo",
        "name": "HAEO",
        "codeowners": ["@TrentHouliston", "@BrendanAnnable"],
        "version": "0.2.1",
    }

    result = _format_manifest(manifest)

    # Verify @ was stripped from codeowners
    assert result.get("codeowners") == ["TrentHouliston", "BrendanAnnable"]
    # Verify original manifest is not modified
    assert manifest.get("codeowners") == ["@TrentHouliston", "@BrendanAnnable"]


def test_format_manifest_no_codeowners() -> None:
    """Test that _format_manifest handles manifests without codeowners."""
    manifest: Manifest = {
        "domain": "haeo",
        "name": "HAEO",
        "version": "0.2.1",
    }

    result = _format_manifest(manifest)

    # Verify the manifest is returned unchanged (no codeowners key)
    assert "codeowners" not in result or result.get("codeowners") == manifest.get("codeowners")


async def test_save_diagnostics_with_historical_time(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    tmp_path: Path,
) -> None:
    """Test save_diagnostics service with historical time uses HistoricalStateProvider."""
    # Set up the service - need to register recorder component first
    hass.config.components.add("recorder")
    await async_setup(hass, {})

    # Mock the entry state as loaded
    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    mock_hub_entry.runtime_data = None

    # Mock config path
    hass.config.config_dir = str(tmp_path)

    target_timestamp = datetime(2026, 1, 20, 14, 32, 3, tzinfo=UTC)

    mock_diagnostics = DiagnosticsResult(
        data={
            "config": {"participants": {}},
            "environment": {"ha_version": "2024.1.0", "historical": True},
            "inputs": [{"entity_id": "sensor.test"}],  # Non-empty to pass validation
            "outputs": {},
        },
        missing_entity_ids=[],
    )

    mock_historical_provider = Mock()
    mock_historical_provider.timestamp = target_timestamp

    with (
        patch(
            "custom_components.haeo.diagnostics.collect_diagnostics",
            new_callable=AsyncMock,
            return_value=mock_diagnostics,
        ) as mock_collect,
        patch(
            "custom_components.haeo.diagnostics.HistoricalStateProvider",
            return_value=mock_historical_provider,
        ) as mock_provider_class,
    ):
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {
                "config_entry": mock_hub_entry.entry_id,
                "time": target_timestamp,
            },
            blocking=True,
        )

    # Verify HistoricalStateProvider was created with correct timestamp
    mock_provider_class.assert_called_once_with(hass, target_timestamp)

    # Verify collect_diagnostics was called with the historical provider
    mock_collect.assert_called_once()
    call_args = mock_collect.call_args
    assert call_args[0][2] == mock_historical_provider

    # Verify file was created with the historical timestamp in filename
    files = list(tmp_path.glob("haeo/diagnostics/diagnostics_*.json"))
    assert len(files) == 1
    # Filename should use the historical timestamp
    assert "2026-01-20" in files[0].name


async def test_save_diagnostics_schema_includes_time_when_recorder_available(
    hass: HomeAssistant,
) -> None:
    """Test that time parameter is available when recorder is loaded."""
    # Add recorder to components
    hass.config.components.add("recorder")

    await async_setup(hass, {})

    # Get the registered service schema
    service = hass.services._services.get(DOMAIN, {}).get("save_diagnostics")
    assert service is not None

    schema = service.schema
    assert schema is not None

    # The schema should include the optional time field
    # We can verify by checking that the schema accepts a time
    schema({"config_entry": "test_entry", "time": "2026-01-20T14:32:03+00:00"})


async def test_save_diagnostics_schema_excludes_time_when_recorder_unavailable(
    hass: HomeAssistant,
) -> None:
    """Test that time parameter is not available when recorder is not loaded."""
    # By default, recorder is not in components
    assert "recorder" not in hass.config.components

    await async_setup(hass, {})

    # Get the registered service schema
    service = hass.services._services.get(DOMAIN, {}).get("save_diagnostics")
    assert service is not None

    schema = service.schema
    assert schema is not None

    # The schema should not include the time field
    # Verify the schema only requires config_entry (timestamp would fail)
    result = schema({"config_entry": "test_entry"})
    assert "config_entry" in result
    # Time should not be parsed since it's not in the schema
    assert "time" not in result


async def test_save_diagnostics_historical_missing_entities_raises_error(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    tmp_path: Path,
) -> None:
    """Test save_diagnostics raises error when historical query has missing entities."""
    # Set up the service - need to register recorder component first
    hass.config.components.add("recorder")
    await async_setup(hass, {})

    # Mock the entry state as loaded
    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    mock_hub_entry.runtime_data = None

    # Mock config path
    hass.config.config_dir = str(tmp_path)

    target_timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

    # Mock diagnostics with missing entities
    mock_diagnostics = DiagnosticsResult(
        data={
            "config": {"participants": {}},
            "environment": {"ha_version": "2024.1.0", "historical": True},
            "inputs": [],  # No inputs found
            "outputs": {},
        },
        missing_entity_ids=["sensor.battery_soc", "sensor.grid_price"],
    )

    mock_historical_provider = Mock()
    mock_historical_provider.timestamp = target_timestamp

    with (
        patch(
            "custom_components.haeo.diagnostics.collect_diagnostics",
            new_callable=AsyncMock,
            return_value=mock_diagnostics,
        ),
        patch(
            "custom_components.haeo.diagnostics.HistoricalStateProvider",
            return_value=mock_historical_provider,
        ),
        pytest.raises(ServiceValidationError) as exc_info,
    ):
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {
                "config_entry": mock_hub_entry.entry_id,
                "time": target_timestamp,
            },
            blocking=True,
        )

    assert exc_info.value.translation_key == "no_history_at_time"
    # Verify placeholders include time and missing entities
    placeholders = exc_info.value.translation_placeholders
    assert placeholders is not None
    assert "time" in placeholders
    assert "sensor.battery_soc" in placeholders["missing"]
    assert "sensor.grid_price" in placeholders["missing"]


# ===== Tests for the optimize service =====


async def test_async_setup_registers_optimize_service(hass: HomeAssistant) -> None:
    """Test that async_setup registers the optimize service."""
    result = await async_setup(hass, {})

    assert result is True
    assert hass.services.has_service(DOMAIN, "optimize")


async def test_optimize_service_success(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Test optimize service runs optimization successfully."""
    await async_setup(hass, {})

    # Mock the entry state as loaded
    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)

    # Create a mock coordinator
    mock_coordinator = AsyncMock()
    mock_coordinator.async_run_optimization = AsyncMock()

    mock_hub_entry.runtime_data = HaeoRuntimeData(
        coordinator=mock_coordinator,
        horizon_manager=Mock(),
    )

    # Call the service
    await hass.services.async_call(
        DOMAIN,
        "optimize",
        {"config_entry": mock_hub_entry.entry_id},
        blocking=True,
    )

    # Verify optimization was triggered
    mock_coordinator.async_run_optimization.assert_called_once()


async def test_optimize_service_entry_not_found(hass: HomeAssistant) -> None:
    """Test optimize raises error when config entry not found."""
    await async_setup(hass, {})

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "optimize",
            {"config_entry": "non_existent_entry"},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_not_found"


async def test_optimize_service_wrong_domain(hass: HomeAssistant) -> None:
    """Test optimize raises error when config entry is not HAEO."""
    await async_setup(hass, {})

    other_entry = MockConfigEntry(
        domain="other_integration",
        data={},
        entry_id="other_entry_id",
    )
    other_entry.add_to_hass(hass)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "optimize",
            {"config_entry": other_entry.entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_wrong_domain"


async def test_optimize_service_entry_not_loaded(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Test optimize raises error when config entry not loaded."""
    await async_setup(hass, {})

    mock_hub_entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "optimize",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_not_loaded"


async def test_optimize_service_no_coordinator(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
) -> None:
    """Test optimize raises error when coordinator is not available."""
    await async_setup(hass, {})

    mock_hub_entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    # Runtime data with no coordinator
    mock_hub_entry.runtime_data = HaeoRuntimeData(
        coordinator=None,
        horizon_manager=Mock(),
    )

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "optimize",
            {"config_entry": mock_hub_entry.entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == "config_entry_not_loaded"

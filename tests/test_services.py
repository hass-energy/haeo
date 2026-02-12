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


async def test_async_setup_registers_services(hass: HomeAssistant) -> None:
    """Test that async_setup registers HAEO services."""
    result = await async_setup(hass, {})

    assert result is True
    assert hass.services.has_service(DOMAIN, "save_diagnostics")
    assert hass.services.has_service(DOMAIN, "optimize")


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

    filename = files[0].name
    assert filename.startswith("diagnostics_")
    assert filename.endswith(".json")

    timestamp_part = filename.replace("diagnostics_", "").replace(".json", "")
    assert len(timestamp_part) == 24
    assert timestamp_part[4] == "-"
    assert timestamp_part[7] == "-"
    assert timestamp_part[10] == "_"
    assert "." in timestamp_part

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


@pytest.mark.parametrize(
    ("scenario", "expected_key"),
    [
        pytest.param("missing_entry", "config_entry_not_found", id="entry_not_found"),
        pytest.param("wrong_domain", "config_entry_wrong_domain", id="wrong_domain"),
        pytest.param("not_loaded", "config_entry_not_loaded", id="entry_not_loaded"),
    ],
)
async def test_save_diagnostics_service_validation_errors(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    scenario: str,
    expected_key: str,
) -> None:
    """save_diagnostics validates config entry references consistently."""
    await async_setup(hass, {})

    if scenario == "missing_entry":
        entry_id = "non_existent_entry"
    elif scenario == "wrong_domain":
        other_entry = MockConfigEntry(
            domain="other_integration",
            data={},
            entry_id="other_entry_id",
        )
        other_entry.add_to_hass(hass)
        entry_id = other_entry.entry_id
    else:
        mock_hub_entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
        entry_id = mock_hub_entry.entry_id

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {"config_entry": entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == expected_key


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
    """Test save_diagnostics service with historical time passes as_of to collector."""
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
            "environment": {"ha_version": "2024.1.0"},
            "inputs": [{"entity_id": "sensor.test"}],  # Non-empty to pass validation
        },
        missing_entity_ids=[],
    )

    with patch(
        "custom_components.haeo.diagnostics.collect_diagnostics",
        new_callable=AsyncMock,
        return_value=mock_diagnostics,
    ) as mock_collect:
        await hass.services.async_call(
            DOMAIN,
            "save_diagnostics",
            {
                "config_entry": mock_hub_entry.entry_id,
                "time": target_timestamp,
            },
            blocking=True,
        )

    # Verify collect_diagnostics was called with as_of=target_timestamp
    mock_collect.assert_called_once()
    call_args = mock_collect.call_args
    assert call_args.kwargs["as_of"] == target_timestamp

    # Verify file was created with the historical timestamp in filename
    files = list(tmp_path.glob("haeo/diagnostics/diagnostics_*.json"))
    assert len(files) == 1
    # Filename should use the historical timestamp
    assert "2026-01-20" in files[0].name


@pytest.mark.parametrize(
    ("recorder_loaded", "expect_time"),
    [
        pytest.param(True, True, id="recorder_loaded"),
        pytest.param(False, False, id="recorder_missing"),
    ],
)
async def test_save_diagnostics_schema_time_field(
    hass: HomeAssistant,
    recorder_loaded: bool,
    expect_time: bool,
) -> None:
    """save_diagnostics exposes time only when recorder is loaded."""
    if recorder_loaded:
        hass.config.components.add("recorder")

    await async_setup(hass, {})

    service = hass.services._services.get(DOMAIN, {}).get("save_diagnostics")
    assert service is not None

    schema = service.schema
    assert schema is not None

    if expect_time:
        schema({"config_entry": "test_entry", "time": "2026-01-20T14:32:03+00:00"})
    else:
        result = schema({"config_entry": "test_entry"})
        assert "config_entry" in result
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

    with (
        patch(
            "custom_components.haeo.diagnostics.collect_diagnostics",
            new_callable=AsyncMock,
            return_value=mock_diagnostics,
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


@pytest.mark.parametrize(
    ("scenario", "expected_key"),
    [
        pytest.param("missing_entry", "config_entry_not_found", id="entry_not_found"),
        pytest.param("wrong_domain", "config_entry_wrong_domain", id="wrong_domain"),
        pytest.param("not_loaded", "config_entry_not_loaded", id="entry_not_loaded"),
    ],
)
async def test_optimize_service_validation_errors(
    hass: HomeAssistant,
    mock_hub_entry: MockConfigEntry,
    scenario: str,
    expected_key: str,
) -> None:
    """Optimize validates config entry references consistently."""
    await async_setup(hass, {})

    if scenario == "missing_entry":
        entry_id = "non_existent_entry"
    elif scenario == "wrong_domain":
        other_entry = MockConfigEntry(
            domain="other_integration",
            data={},
            entry_id="other_entry_id",
        )
        other_entry.add_to_hass(hass)
        entry_id = other_entry.entry_id
    else:
        mock_hub_entry._async_set_state(hass, ConfigEntryState.NOT_LOADED, None)
        entry_id = mock_hub_entry.entry_id

    with pytest.raises(ServiceValidationError) as exc_info:
        await hass.services.async_call(
            DOMAIN,
            "optimize",
            {"config_entry": entry_id},
            blocking=True,
        )

    assert exc_info.value.translation_key == expected_key


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

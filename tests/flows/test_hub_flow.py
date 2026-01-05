"""Test hub configuration flow - 100% coverage."""

from typing import Any

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.flows import (
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESET_CUSTOM,
    HORIZON_PRESETS,
)
from custom_components.haeo.flows.hub import HubConfigFlow


async def test_user_flow_success_with_preset(hass: HomeAssistant) -> None:
    """Test successful hub creation via user flow with a preset."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert result.get("errors") == {}

    # Configure with preset (should create entry directly, no second step)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Test Hub"
    data = result.get("data")
    assert data is not None
    assert data[CONF_NAME] == "Test Hub"
    assert data["integration_type"] == INTEGRATION_TYPE_HUB

    # Verify preset is stored in entry data
    assert data[CONF_HORIZON_PRESET] == HORIZON_PRESET_3_DAYS

    # Verify preset values were applied
    preset_values = HORIZON_PRESETS[HORIZON_PRESET_3_DAYS]
    assert data[CONF_TIER_1_DURATION] == preset_values[CONF_TIER_1_DURATION]
    assert data[CONF_TIER_1_COUNT] == preset_values[CONF_TIER_1_COUNT]
    assert data[CONF_TIER_4_COUNT] == preset_values[CONF_TIER_4_COUNT]

    # Verify entry was created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].title == "Test Hub"


async def test_user_flow_custom_preset_shows_second_step(hass: HomeAssistant) -> None:
    """Test that selecting Custom preset shows the custom_tiers step."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Select Custom preset
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Custom Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM,
        },
    )

    # Should show custom_tiers step
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "custom_tiers"

    # Verify tier fields are in the schema
    data_schema = result.get("data_schema")
    assert data_schema is not None
    field_names = {key.schema for key in data_schema.schema}
    assert CONF_TIER_1_DURATION in field_names
    assert CONF_TIER_1_COUNT in field_names
    assert CONF_TIER_4_COUNT in field_names


async def test_user_flow_custom_tiers_creates_entry(hass: HomeAssistant) -> None:
    """Test that completing custom_tiers step creates the entry."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # First step: select Custom
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Custom Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM,
        },
    )

    assert result.get("step_id") == "custom_tiers"

    # Second step: provide custom tier values
    custom_tier_4_count = 96  # 96 intervals of 120 min = 8 days
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TIER_1_COUNT: 10,
            CONF_TIER_1_DURATION: 2,
            CONF_TIER_2_COUNT: 12,
            CONF_TIER_2_DURATION: 10,
            CONF_TIER_3_COUNT: 24,
            CONF_TIER_3_DURATION: 60,
            CONF_TIER_4_COUNT: custom_tier_4_count,
            CONF_TIER_4_DURATION: 120,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Custom Hub"
    data = result.get("data")
    assert data is not None

    # Verify preset is stored as custom
    assert data[CONF_HORIZON_PRESET] == HORIZON_PRESET_CUSTOM

    # Verify custom values were used
    assert data[CONF_TIER_1_COUNT] == 10
    assert data[CONF_TIER_1_DURATION] == 2
    assert data[CONF_TIER_4_COUNT] == custom_tier_4_count
    # Verify defaults were used for update interval and debounce (they're hidden during add)
    assert data[CONF_UPDATE_INTERVAL_MINUTES] == DEFAULT_UPDATE_INTERVAL_MINUTES
    assert data[CONF_DEBOUNCE_SECONDS] == DEFAULT_DEBOUNCE_SECONDS


async def test_user_flow_different_presets(hass: HomeAssistant) -> None:
    """Test that different presets apply correct tier values."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    # Use 5-day preset
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "5 Day Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None

    # Verify 5-day preset values
    preset_values = HORIZON_PRESETS[HORIZON_PRESET_5_DAYS]
    assert data[CONF_TIER_4_COUNT] == preset_values[CONF_TIER_4_COUNT]
    assert data[CONF_TIER_4_COUNT] == 96  # 96 intervals of 60 min for 5 days


async def test_user_flow_duplicate_name(hass: HomeAssistant) -> None:
    """Test that duplicate hub names are rejected."""
    # Create existing hub
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Existing Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        title="Existing Hub",
    )
    existing_entry.add_to_hass(hass)

    # Try to create hub with same name
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Existing Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
        },
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_NAME: "name_exists"}

    # Verify flow can recover from error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "New Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "New Hub"


async def test_user_flow_unique_id_prevents_duplicate(hass: HomeAssistant) -> None:
    """Test that unique_id prevents duplicate hub configurations."""
    # Create first hub
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Try to create hub with same name (case-insensitive, spaces normalized)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "test hub",  # Same name, different case
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
        },
    )

    # Should be rejected due to unique_id check
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_user_flow_default_values(hass: HomeAssistant) -> None:
    """Test that default values are suggested in the form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result.get("type") == FlowResultType.FORM
    data_schema = result.get("data_schema")
    assert data_schema is not None

    # Check suggested values exist in the schema
    schema_keys = {vol_key.schema: vol_key for vol_key in data_schema.schema}

    # Verify default horizon preset is 5 days
    assert schema_keys[CONF_HORIZON_PRESET].default() == HORIZON_PRESET_5_DAYS


async def test_hub_supports_subentry_types(hass: HomeAssistant) -> None:
    """Test that hub correctly advertises supported subentry types."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_ADVANCED_MODE: True,  # Required for connection, node, battery_section flows
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Get supported subentry types
    subentry_types = HubConfigFlow.async_get_supported_subentry_types(hub_entry)

    # Should include all element types when advanced_mode is enabled
    assert set(subentry_types.keys()) == set(ELEMENT_TYPES)

    # Verify each type has a flow class
    for flow_class in subentry_types.values():
        assert flow_class is not None
        assert hasattr(flow_class, "async_step_user")
        assert hasattr(flow_class, "async_step_reconfigure")


async def test_subentry_translations_exist(hass: HomeAssistant, configurable_entity: None) -> None:
    """Ensure all element subentry flows expose complete translations."""

    hub_entry = MockConfigEntry()
    hub_entry.add_to_hass(hass)

    translations = await async_get_translations(
        hass, "en", "config_subentries", integrations=[DOMAIN], config_flow=True
    )

    subentry_flows = HubConfigFlow.async_get_supported_subentry_types(hub_entry)

    common_suffixes = (
        "flow_title",
        "entry_type",
        "initiate_flow.user",
        "initiate_flow.reconfigure",
        "step.user.title",
        "step.user.description",
        "step.reconfigure.title",
        "step.reconfigure.description",
        "error.name_exists",
        "error.missing_name",
    )

    for element_type, flow_class in subentry_flows.items():
        base_key = f"component.{DOMAIN}.config_subentries.{element_type}"

        for suffix in common_suffixes:
            assert f"{base_key}.{suffix}" in translations, f"Missing translation key {base_key}.{suffix}"

        flow: Any = flow_class()
        flow.hass = hass
        flow.handler = (hub_entry.entry_id, element_type)

        step_result = await flow.async_step_user(user_input=None)
        assert step_result.get("type") == FlowResultType.FORM

        schema = step_result.get("data_schema")
        if schema is None:
            continue

        for field in schema.schema:
            field_name = field.schema
            assert f"{base_key}.step.user.data.{field_name}" in translations, (
                f"Missing translation for {element_type} field '{field_name}'"
            )

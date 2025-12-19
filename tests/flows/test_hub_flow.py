"""Test hub configuration flow - 100% coverage."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_UNTIL,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_UNTIL,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_UNTIL,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_UNTIL,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_1_UNTIL,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_2_UNTIL,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_3_UNTIL,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_TIER_4_UNTIL,
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
from custom_components.haeo.flows.element import ElementSubentryFlow
from custom_components.haeo.flows.hub import HubConfigFlow


async def test_user_flow_success_with_preset(hass: HomeAssistant) -> None:
    """Test successful hub creation via user flow with a preset."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert result.get("errors") == {}

    # Configure with preset (should create entry directly, no second step)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Test Hub"
    data = result.get("data")
    assert data is not None
    assert data[CONF_NAME] == "Test Hub"
    assert data["integration_type"] == INTEGRATION_TYPE_HUB

    # Verify preset values were applied
    preset_values = HORIZON_PRESETS[HORIZON_PRESET_3_DAYS]
    assert data[CONF_TIER_1_DURATION] == preset_values[CONF_TIER_1_DURATION]
    assert data[CONF_TIER_1_UNTIL] == preset_values[CONF_TIER_1_UNTIL]
    assert data[CONF_TIER_4_UNTIL] == preset_values[CONF_TIER_4_UNTIL]

    # Verify entry was created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].title == "Test Hub"


async def test_user_flow_custom_preset_shows_second_step(hass: HomeAssistant) -> None:
    """Test that selecting Custom preset shows the custom_tiers step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Select Custom preset
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Custom Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
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
    assert CONF_TIER_1_UNTIL in field_names
    assert CONF_TIER_4_UNTIL in field_names


async def test_user_flow_custom_tiers_creates_entry(hass: HomeAssistant) -> None:
    """Test that completing custom_tiers step creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # First step: select Custom
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Custom Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_CUSTOM,
            CONF_UPDATE_INTERVAL_MINUTES: 10,
            CONF_DEBOUNCE_SECONDS: 3,
        },
    )

    assert result.get("step_id") == "custom_tiers"

    # Second step: provide custom tier values
    custom_tier_4_until = 5760  # 4 days
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_TIER_1_DURATION: 2,
            CONF_TIER_1_UNTIL: 10,
            CONF_TIER_2_DURATION: 10,
            CONF_TIER_2_UNTIL: 120,
            CONF_TIER_3_DURATION: 60,
            CONF_TIER_3_UNTIL: 1440,
            CONF_TIER_4_DURATION: 120,
            CONF_TIER_4_UNTIL: custom_tier_4_until,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "Custom Hub"
    data = result.get("data")
    assert data is not None

    # Verify custom values were used
    assert data[CONF_TIER_1_DURATION] == 2
    assert data[CONF_TIER_1_UNTIL] == 10
    assert data[CONF_TIER_4_UNTIL] == custom_tier_4_until
    assert data[CONF_UPDATE_INTERVAL_MINUTES] == 10
    assert data[CONF_DEBOUNCE_SECONDS] == 3


async def test_user_flow_different_presets(hass: HomeAssistant) -> None:
    """Test that different presets apply correct tier values."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    # Use 5-day preset
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "5 Day Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_5_DAYS,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None

    # Verify 5-day preset values
    preset_values = HORIZON_PRESETS[HORIZON_PRESET_5_DAYS]
    assert data[CONF_TIER_4_UNTIL] == preset_values[CONF_TIER_4_UNTIL]
    assert data[CONF_TIER_4_UNTIL] == 7200  # 5 days in minutes


async def test_user_flow_duplicate_name(hass: HomeAssistant) -> None:
    """Test that duplicate hub names are rejected."""
    # Create existing hub
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Existing Hub",
            CONF_TIER_1_UNTIL: DEFAULT_TIER_1_UNTIL,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        title="Existing Hub",
    )
    existing_entry.add_to_hass(hass)

    # Try to create hub with same name
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Existing Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
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
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("title") == "New Hub"


async def test_user_flow_unique_id_prevents_duplicate(hass: HomeAssistant) -> None:
    """Test that unique_id prevents duplicate hub configurations."""
    # Create first hub
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Try to create hub with same name (case-insensitive, spaces normalized)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "test hub",  # Same name, different case
            CONF_HORIZON_PRESET: HORIZON_PRESET_3_DAYS,
            CONF_UPDATE_INTERVAL_MINUTES: DEFAULT_UPDATE_INTERVAL_MINUTES,
            CONF_DEBOUNCE_SECONDS: DEFAULT_DEBOUNCE_SECONDS,
        },
    )

    # Should be rejected due to unique_id check
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "already_configured"


async def test_user_flow_default_values(hass: HomeAssistant) -> None:
    """Test that default values are suggested in the form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result.get("type") == FlowResultType.FORM
    data_schema = result.get("data_schema")
    assert data_schema is not None

    # Check suggested values exist in the schema
    schema_keys = {vol_key.schema: vol_key for vol_key in data_schema.schema}

    # Verify default horizon preset is 3 days
    assert schema_keys[CONF_HORIZON_PRESET].default() == HORIZON_PRESET_3_DAYS


async def test_hub_supports_subentry_types(hass: HomeAssistant) -> None:
    """Test that hub correctly advertises supported subentry types."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_UNTIL: DEFAULT_TIER_1_UNTIL,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="test_hub_id",
    )
    hub_entry.add_to_hass(hass)

    # Get supported subentry types
    subentry_types = HubConfigFlow.async_get_supported_subentry_types(hub_entry)

    # Should include all element types plus network (which is registered separately)
    assert set(subentry_types.keys()) == set(ELEMENT_TYPES)

    # Verify each type has a flow class
    for flow_class in subentry_types.values():
        assert flow_class is not None
        assert hasattr(flow_class, "async_step_user")
        assert hasattr(flow_class, "async_step_reconfigure")


async def test_subentry_translations_exist(hass: HomeAssistant) -> None:
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
            assert f"{base_key}.{suffix}" in translations, (
                f"Missing translation key {base_key}.{suffix}"
            )

        flow = flow_class()
        assert isinstance(flow, ElementSubentryFlow)

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

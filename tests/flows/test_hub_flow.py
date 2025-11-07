"""Test hub configuration flow - 100% coverage."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import (
    CONF_HORIZON_HOURS,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_PERIOD_MINUTES,
    DOMAIN,
    INTEGRATION_TYPE_HUB,
)
from custom_components.haeo.elements import ELEMENT_TYPES
from custom_components.haeo.flows.hub import HubConfigFlow


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Test successful hub creation via user flow."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {}

    # Configure with valid data
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 48,
            CONF_PERIOD_MINUTES: 5,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Hub"
    assert result["data"][CONF_NAME] == "Test Hub"
    assert result["data"]["integration_type"] == INTEGRATION_TYPE_HUB
    assert result["data"][CONF_HORIZON_HOURS] == 48
    assert result["data"][CONF_PERIOD_MINUTES] == 5

    # Verify entry was created
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].title == "Test Hub"


async def test_user_flow_duplicate_name(hass: HomeAssistant) -> None:
    """Test that duplicate hub names are rejected."""
    # Create existing hub
    existing_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Existing Hub",
            CONF_HORIZON_HOURS: DEFAULT_HORIZON_HOURS,
            CONF_PERIOD_MINUTES: DEFAULT_PERIOD_MINUTES,
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
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 10,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_NAME: "name_exists"}

    # Verify flow can recover from error
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "New Hub",
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 10,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "New Hub"


async def test_user_flow_unique_id_prevents_duplicate(hass: HomeAssistant) -> None:
    """Test that unique_id prevents duplicate hub configurations."""
    # Create first hub
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: 48,
            CONF_PERIOD_MINUTES: 5,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Try to create hub with same name (case-insensitive, spaces normalized)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_NAME: "test hub",  # Same name, different case
            CONF_HORIZON_HOURS: 24,
            CONF_PERIOD_MINUTES: 10,
        },
    )

    # Should be rejected due to unique_id check
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_default_values(hass: HomeAssistant) -> None:
    """Test that default values are suggested in the form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})

    assert result["type"] == FlowResultType.FORM
    assert result["data_schema"] is not None

    # Check suggested values exist in the schema
    schema_keys = {vol_key.schema: vol_key for vol_key in result["data_schema"].schema}

    # Verify default values
    assert schema_keys[CONF_HORIZON_HOURS].default() == DEFAULT_HORIZON_HOURS
    assert schema_keys[CONF_PERIOD_MINUTES].default() == DEFAULT_PERIOD_MINUTES


async def test_hub_supports_subentry_types(hass: HomeAssistant) -> None:
    """Test that hub correctly advertises supported subentry types."""
    # Create hub entry
    hub_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "integration_type": INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_HORIZON_HOURS: DEFAULT_HORIZON_HOURS,
            CONF_PERIOD_MINUTES: DEFAULT_PERIOD_MINUTES,
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
        hass,
        "en",
        "config_subentries",
        integrations=[DOMAIN],
        config_flow=True,
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

        flow = flow_class()
        flow.hass = hass
        flow.handler = (hub_entry.entry_id, element_type)

        step_result = await flow.async_step_user(user_input=None)
        assert step_result["type"] == FlowResultType.FORM

        schema = step_result["data_schema"]
        if schema is None:
            continue

        for field in schema.schema:
            field_name = field.schema
            assert f"{base_key}.step.user.data.{field_name}" in translations, (
                f"Missing translation for {element_type} field '{field_name}'"
            )

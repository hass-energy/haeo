"""Unit tests for hub configuration flow helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations

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
    DOMAIN,
)
from custom_components.haeo.flows import (
    HORIZON_PRESET_5_DAYS,
    get_custom_tiers_schema,
    get_hub_setup_schema,
    get_network_config_schema,
)
from custom_components.haeo.flows.hub import HubConfigFlow

# Test data for hub flow
VALID_DATA = [
    {
        "description": "Basic hub configuration",
        "config": {
            CONF_NAME: "Test Hub",
        },
    },
]

INVALID_DATA = [
    {
        "description": "Empty config should fail validation",
        "config": {},
        "error": "cannot be empty",
    },
]


async def test_user_step_translations_loadable(hass: HomeAssistant) -> None:
    """Test that initial user step translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    # Check that key config flow translations exist
    assert f"component.{DOMAIN}.config.step.user.title" in translations
    assert f"component.{DOMAIN}.config.step.user.data.name" in translations
    assert f"component.{DOMAIN}.config.step.user.data.horizon_preset" in translations


async def test_custom_tiers_step_translations_loadable(hass: HomeAssistant) -> None:
    """Test that custom_tiers step translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    # Check that custom_tiers step translations exist
    assert f"component.{DOMAIN}.config.step.custom_tiers.title" in translations
    assert f"component.{DOMAIN}.config.step.custom_tiers.data.tier_1_duration" in translations
    assert f"component.{DOMAIN}.config.step.custom_tiers.data.tier_1_until" in translations


async def test_user_step_form_has_translations(hass: HomeAssistant) -> None:
    """Test that user step form fields all have translations."""
    flow = HubConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Get translations
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    # Verify all form fields have translations
    data_schema = result.get("data_schema")
    assert data_schema is not None
    schema = data_schema.schema
    for key in schema:
        field_name = key.schema
        translation_key = f"component.{DOMAIN}.config.step.user.data.{field_name}"
        assert translation_key in translations, f"Missing translation for field '{field_name}'"


async def test_config_error_translations_exist(hass: HomeAssistant) -> None:
    """Test that error translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)
    assert f"component.{DOMAIN}.config.error.name_exists" in translations


async def test_config_abort_translations_exist(hass: HomeAssistant) -> None:
    """Test that abort reason translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)
    assert f"component.{DOMAIN}.config.abort.already_configured" in translations


async def test_hub_setup_schema_has_expected_fields(hass: HomeAssistant) -> None:
    """Test that the hub setup schema has the expected simplified fields."""
    schema = get_hub_setup_schema()

    # Get field names from schema
    field_names = {key.schema for key in schema.schema}

    # Verify expected fields are present
    assert CONF_NAME in field_names
    assert CONF_HORIZON_PRESET in field_names
    assert CONF_UPDATE_INTERVAL_MINUTES in field_names
    assert CONF_DEBOUNCE_SECONDS in field_names

    # Verify tier fields are NOT in the simplified schema
    assert CONF_TIER_1_DURATION not in field_names
    assert CONF_TIER_1_UNTIL not in field_names


async def test_custom_tiers_schema_has_tier_fields(hass: HomeAssistant) -> None:
    """Test that the custom tiers schema has all tier configuration fields."""
    schema = get_custom_tiers_schema()

    # Get field names from schema
    field_names = {key.schema for key in schema.schema}

    # Verify all tier fields are present
    assert CONF_TIER_1_DURATION in field_names
    assert CONF_TIER_1_UNTIL in field_names
    assert CONF_TIER_2_DURATION in field_names
    assert CONF_TIER_2_UNTIL in field_names
    assert CONF_TIER_3_DURATION in field_names
    assert CONF_TIER_3_UNTIL in field_names
    assert CONF_TIER_4_DURATION in field_names
    assert CONF_TIER_4_UNTIL in field_names


async def test_schema_coerces_floats_to_integers(hass: HomeAssistant) -> None:
    """Test that the schema coerces float values to integers for tier durations and until values."""
    schema = get_network_config_schema()

    # Simulate float values that might come from JSON or UI
    test_data = {
        CONF_NAME: "Test Hub",
        CONF_TIER_1_DURATION: 1.0,  # Float input
        CONF_TIER_1_UNTIL: 5.0,  # Float input
        CONF_TIER_2_DURATION: 5.0,
        CONF_TIER_2_UNTIL: 60.0,
        CONF_TIER_3_DURATION: 30.0,
        CONF_TIER_3_UNTIL: 1440.0,
        CONF_TIER_4_DURATION: 60.0,
        CONF_TIER_4_UNTIL: 4320.0,
    }

    # Validate and coerce the data
    validated_data = schema(test_data)

    # Verify that floats were coerced to integers
    assert isinstance(validated_data[CONF_TIER_1_DURATION], int), "tier_1_duration should be coerced to int"
    assert isinstance(validated_data[CONF_TIER_1_UNTIL], int), "tier_1_until should be coerced to int"
    assert validated_data[CONF_TIER_1_DURATION] == 1
    assert validated_data[CONF_TIER_1_UNTIL] == 5


async def test_hub_setup_schema_default_preset(hass: HomeAssistant) -> None:
    """Test that the hub setup schema defaults to 5 days preset."""
    schema = get_hub_setup_schema()

    # Find the horizon_preset field
    schema_keys = {vol_key.schema: vol_key for vol_key in schema.schema}
    assert CONF_HORIZON_PRESET in schema_keys, "CONF_HORIZON_PRESET not found in schema"
    assert schema_keys[CONF_HORIZON_PRESET].default() == HORIZON_PRESET_5_DAYS

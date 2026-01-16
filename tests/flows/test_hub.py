"""Unit tests for hub configuration flow helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_DURATION_MINUTES,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_HORIZON_DURATION_MINUTES,
    DOMAIN,
)
from custom_components.haeo.flows import (
    CONF_HORIZON_DAYS,
    get_custom_tiers_schema,
    get_default_tier_config,
    get_hub_setup_schema,
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
    assert f"component.{DOMAIN}.config.step.user.data.horizon_days" in translations


async def test_custom_tiers_step_translations_loadable(hass: HomeAssistant) -> None:
    """Test that custom_tiers step translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    # Check that custom_tiers step translations exist
    assert f"component.{DOMAIN}.config.step.custom_tiers.title" in translations
    assert f"component.{DOMAIN}.config.step.custom_tiers.data.tier_1_duration" in translations
    assert f"component.{DOMAIN}.config.step.custom_tiers.data.tier_1_count" in translations


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
    # The UI uses horizon_days, which is converted to horizon_duration_minutes in the flow handler
    assert CONF_HORIZON_DAYS in field_names

    # Verify update interval and debounce are NOT in the add flow (only in options/edit)
    assert CONF_UPDATE_INTERVAL_MINUTES not in field_names
    assert CONF_DEBOUNCE_SECONDS not in field_names

    # Verify tier fields are NOT in the simplified schema
    assert CONF_TIER_1_DURATION not in field_names
    assert CONF_TIER_1_COUNT not in field_names


async def test_custom_tiers_schema_has_tier_fields(hass: HomeAssistant) -> None:
    """Test that the custom tiers schema has all tier configuration fields."""
    schema = get_custom_tiers_schema()

    # Get field names from schema
    field_names = {key.schema for key in schema.schema}

    # Verify tier fields are present (tier_4_count is no longer used - computed at runtime)
    assert CONF_TIER_1_DURATION in field_names
    assert CONF_TIER_1_COUNT in field_names
    assert CONF_TIER_2_DURATION in field_names
    assert CONF_TIER_2_COUNT in field_names
    assert CONF_TIER_3_DURATION in field_names
    assert CONF_TIER_3_COUNT in field_names
    assert CONF_TIER_4_DURATION in field_names
    assert CONF_HORIZON_DURATION_MINUTES in field_names


async def test_schema_coerces_floats_to_integers(hass: HomeAssistant) -> None:
    """Test that the schema coerces float values to integers for tier counts and durations."""
    schema = get_custom_tiers_schema()

    # Simulate float values that might come from JSON or UI
    test_data = {
        CONF_TIER_1_COUNT: 5.0,  # Float input
        CONF_TIER_1_DURATION: 1.0,  # Float input
        CONF_TIER_2_COUNT: 6.0,
        CONF_TIER_2_DURATION: 5.0,
        CONF_TIER_3_COUNT: 4.0,
        CONF_TIER_3_DURATION: 30.0,
        CONF_TIER_4_DURATION: 60.0,
        CONF_HORIZON_DURATION_MINUTES: 7200.0,  # 5 days
    }

    # Validate and coerce the data
    validated_data = schema(test_data)

    # Verify that floats were coerced to integers
    assert isinstance(validated_data[CONF_TIER_1_COUNT], int), "tier_1_count should be coerced to int"
    assert isinstance(validated_data[CONF_TIER_1_DURATION], int), "tier_1_duration should be coerced to int"
    assert validated_data[CONF_TIER_1_COUNT] == 5
    assert validated_data[CONF_TIER_1_DURATION] == 1


async def test_hub_setup_schema_default_horizon(hass: HomeAssistant) -> None:
    """Test that the hub setup schema defaults to 5 days horizon."""
    schema = get_hub_setup_schema()

    # Find the horizon_days field (UI input, converted to minutes in flow handler)
    schema_keys = {vol_key.schema: vol_key for vol_key in schema.schema}
    assert CONF_HORIZON_DAYS in schema_keys, "CONF_HORIZON_DAYS not found in schema"
    # Default is 5 days (shown as 5 in the UI slider)
    assert schema_keys[CONF_HORIZON_DAYS].default() == 5


def test_get_default_tier_config() -> None:
    """Test get_default_tier_config returns expected values."""
    config = get_default_tier_config()

    assert config[CONF_TIER_1_COUNT] == 5
    assert config[CONF_TIER_1_DURATION] == 1
    assert config[CONF_TIER_2_COUNT] == 6
    assert config[CONF_TIER_2_DURATION] == 5
    assert config[CONF_TIER_3_COUNT] == 4
    assert config[CONF_TIER_3_DURATION] == 30
    assert config[CONF_TIER_4_DURATION] == 60
    assert config[CONF_HORIZON_DURATION_MINUTES] == DEFAULT_HORIZON_DURATION_MINUTES


def test_get_default_tier_config_with_custom_horizon() -> None:
    """Test get_default_tier_config with custom horizon."""
    horizon = 3 * 24 * 60  # 3 days
    config = get_default_tier_config(horizon)

    assert config[CONF_HORIZON_DURATION_MINUTES] == horizon

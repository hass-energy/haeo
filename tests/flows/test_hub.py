"""Unit tests for hub configuration flow helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations

from custom_components.haeo.const import CONF_HORIZON_HOURS, CONF_NAME, CONF_OPTIMIZER, CONF_PERIOD_MINUTES, DOMAIN
from custom_components.haeo.flows import get_network_config_schema
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
    assert f"component.{DOMAIN}.config.step.user.data.horizon_hours" in translations
    assert f"component.{DOMAIN}.config.step.user.data.period_minutes" in translations
    assert f"component.{DOMAIN}.config.step.user.data.optimizer" in translations


async def test_user_step_form_has_translations(hass: HomeAssistant) -> None:
    """Test that user step form fields all have translations."""
    flow = HubConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Get translations
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    # Verify all form fields have translations
    assert result["data_schema"] is not None
    schema = result["data_schema"].schema
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


async def test_schema_coerces_floats_to_integers(hass: HomeAssistant) -> None:
    """Test that the schema coerces float values to integers for horizon_hours and period_minutes."""
    schema = get_network_config_schema()

    # Simulate float values that might come from JSON or UI
    test_data = {
        CONF_NAME: "Test Hub",
        CONF_HORIZON_HOURS: 24.0,  # Float input
        CONF_PERIOD_MINUTES: 5.0,  # Float input
        CONF_OPTIMIZER: "highs",
    }

    # Validate and coerce the data
    validated_data = schema(test_data)

    # Verify that floats were coerced to integers
    assert isinstance(validated_data[CONF_HORIZON_HOURS], int), "horizon_hours should be coerced to int"
    assert isinstance(validated_data[CONF_PERIOD_MINUTES], int), "period_minutes should be coerced to int"
    assert validated_data[CONF_HORIZON_HOURS] == 24
    assert validated_data[CONF_PERIOD_MINUTES] == 5

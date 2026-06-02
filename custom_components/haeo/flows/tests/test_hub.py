"""Unit tests for hub configuration flow helpers."""

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.translation import async_get_translations
import pytest
import voluptuous as vol

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_DEBOUNCE_SECONDS, CONF_HORIZON, CONF_NAME
import custom_components.haeo.flows as flows_module
from custom_components.haeo.flows import HORIZON_PRESET_5_DAYS, get_hub_setup_schema
from custom_components.haeo.flows.hub import HubConfigFlow


async def test_user_step_translations_loadable(hass: HomeAssistant) -> None:
    """Test that initial user step translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    assert f"component.{DOMAIN}.config.step.user.title" in translations
    assert f"component.{DOMAIN}.config.step.user.sections.common.name" in translations
    assert f"component.{DOMAIN}.config.step.user.sections.common.data.name" in translations
    assert f"component.{DOMAIN}.config.step.user.sections.common.data.horizon" in translations


async def test_user_step_form_has_translations(hass: HomeAssistant) -> None:
    """Test that user step form fields all have translations."""
    flow = HubConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)

    data_schema = result.get("data_schema")
    assert data_schema is not None
    schema = data_schema.schema
    for section_key, section_schema in schema.items():
        section_name = section_key.schema
        section_translation = f"component.{DOMAIN}.config.step.user.sections.{section_name}.name"
        assert section_translation in translations, f"Missing section translation '{section_translation}'"
        for field in section_schema.schema.schema:
            field_name = field.schema
            translation_key = f"component.{DOMAIN}.config.step.user.sections.{section_name}.data.{field_name}"
            assert translation_key in translations, f"Missing translation for field '{field_name}'"


async def test_config_error_translations_exist(hass: HomeAssistant) -> None:
    """Test that error translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)
    assert f"component.{DOMAIN}.config.error.name_exists" in translations
    assert f"component.{DOMAIN}.config.error.invalid_horizon_entity" in translations


async def test_config_abort_translations_exist(hass: HomeAssistant) -> None:
    """Test that abort reason translations can be loaded."""
    translations = await async_get_translations(hass, "en", "config", integrations=[DOMAIN], config_flow=True)
    assert f"component.{DOMAIN}.config.abort.already_configured" in translations


async def test_hub_setup_schema_has_expected_fields(hass: HomeAssistant) -> None:
    """Test that the hub setup schema has the expected simplified fields."""
    schema = get_hub_setup_schema()

    common_section = schema.schema[vol.Required(flows_module.HUB_SECTION_COMMON)]
    field_names = {key.schema for key in common_section.schema.schema}

    assert CONF_NAME in field_names
    assert CONF_HORIZON in field_names
    assert CONF_DEBOUNCE_SECONDS not in field_names


async def test_hub_setup_schema_default_preset(hass: HomeAssistant) -> None:
    """Test that the hub setup schema defaults to 5 days preset."""
    schema = get_hub_setup_schema()

    common_section = schema.schema[vol.Required(flows_module.HUB_SECTION_COMMON)]
    schema_keys = {vol_key.schema: vol_key for vol_key in common_section.schema.schema}
    assert CONF_HORIZON in schema_keys
    assert schema_keys[CONF_HORIZON].default() == HORIZON_PRESET_5_DAYS


def test_create_horizon_preset_raises_on_invalid_days() -> None:
    """Test _create_horizon_preset raises ValueError for days < 2."""
    with pytest.raises(ValueError, match="Horizon must be at least 2 days"):
        flows_module._create_horizon_preset(1)

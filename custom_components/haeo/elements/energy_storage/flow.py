"""Energy storage element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import EntityMetadata, extract_entity_metadata
from custom_components.haeo.schema.util import UnitSpec

from .schema import CONF_CAPACITY, CONF_INITIAL_CHARGE, ELEMENT_TYPE, EnergyStorageConfigSchema

# Unit specifications
ENERGY_UNITS: UnitSpec = UnitOfEnergy


def _filter_incompatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that are NOT compatible with the accepted units."""
    return [v.entity_id for v in entity_metadata if not v.is_compatible_with(accepted_units)]


def _build_schema(entity_metadata: list[EntityMetadata]) -> vol.Schema:
    """Build the voluptuous schema for energy storage configuration."""
    incompatible_energy = _filter_incompatible_entities(entity_metadata, ENERGY_UNITS)

    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CAPACITY): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_energy,
                )
            ),
            vol.Required(CONF_INITIAL_CHARGE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_energy,
                )
            ),
        }
    )


class EnergyStorageSubentryFlowHandler(ConfigSubentryFlow):
    """Handle energy storage element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new energy storage element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("EnergyStorageConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_schema(entity_metadata)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing energy storage element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("EnergyStorageConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        entity_metadata = extract_entity_metadata(self.hass)
        schema = _build_schema(entity_metadata)
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry."""
        current_id = self._get_current_subentry_id()
        return {
            subentry.title for subentry in self._get_entry().subentries.values() if subentry.subentry_id != current_id
        }

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None

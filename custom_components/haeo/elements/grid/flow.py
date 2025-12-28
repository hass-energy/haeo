"""Grid element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import EntityMetadata, extract_entity_metadata
from custom_components.haeo.schema.util import UnitSpec

from .schema import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    ELEMENT_TYPE,
    GridConfigSchema,
)

# Price unit pattern: any currency / any energy unit
PRICE_UNITS: list[UnitSpec] = [("*", "/", unit.value) for unit in UnitOfEnergy]


def _filter_incompatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that are NOT compatible with the accepted units."""
    return [v.entity_id for v in entity_metadata if not v.is_compatible_with(accepted_units)]


def _build_participant_selector(participants: list[str], current_value: str | None = None) -> vol.All:
    """Build a selector for choosing element names from participants."""
    options_list = list(participants)
    if current_value and current_value not in options_list:
        options_list.append(current_value)

    options: list[SelectOptionDict] = [SelectOptionDict(value=p, label=p) for p in options_list]
    return vol.All(
        vol.Coerce(str),
        vol.Strip,
        vol.Length(min=1, msg="Element name cannot be empty"),
        SelectSelector(SelectSelectorConfig(options=options, mode=SelectSelectorMode.DROPDOWN)),
    )


def _build_schema(
    entity_metadata: list[EntityMetadata],
    participants: list[str],
    current_connection: str | None = None,
) -> vol.Schema:
    """Build the voluptuous schema for grid configuration."""
    incompatible_price = _filter_incompatible_entities(entity_metadata, PRICE_UNITS)

    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): _build_participant_selector(participants, current_connection),
            vol.Required(CONF_IMPORT_PRICE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_price,
                )
            ),
            vol.Required(CONF_EXPORT_PRICE): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_price,
                )
            ),
            vol.Optional(CONF_IMPORT_LIMIT): vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=0,
                        step="any",
                        unit_of_measurement=UnitOfPower.KILO_WATT,
                    )
                ),
            ),
            vol.Optional(CONF_EXPORT_LIMIT): vol.All(
                vol.Coerce(float),
                vol.Range(min=0, min_included=True, msg="Value must be positive"),
                NumberSelector(
                    NumberSelectorConfig(
                        mode=NumberSelectorMode.BOX,
                        min=0,
                        step="any",
                        unit_of_measurement=UnitOfPower.KILO_WATT,
                    )
                ),
            ),
        }
    )


class GridSubentryFlowHandler(ConfigSubentryFlow):
    """Handle grid element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new grid element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("GridConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Grid")

        entity_metadata = extract_entity_metadata(self.hass)
        participants = self._get_participant_names()
        schema = _build_schema(entity_metadata, participants)
        schema = self.add_suggested_values_to_schema(schema, {CONF_NAME: default_name})

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing grid element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("GridConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        entity_metadata = extract_entity_metadata(self.hass)
        current_connection = subentry.data.get(CONF_CONNECTION)
        participants = self._get_participant_names()
        schema = _build_schema(
            entity_metadata,
            participants,
            current_connection=current_connection if isinstance(current_connection, str) else None,
        )
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

    def _get_participant_names(self) -> list[str]:
        """Return element names available as connection endpoints."""
        # Import here to avoid circular dependency
        from custom_components.haeo.const import CONF_ADVANCED_MODE  # noqa: PLC0415
        from custom_components.haeo.elements import ELEMENT_TYPES, ConnectivityLevel  # noqa: PLC0415

        hub_entry = self._get_entry()
        advanced_mode = hub_entry.data.get(CONF_ADVANCED_MODE, False)
        current_id = self._get_current_subentry_id()

        result: list[str] = []
        for subentry in hub_entry.subentries.values():
            if subentry.subentry_id == current_id:
                continue

            element_type = subentry.data.get(CONF_ELEMENT_TYPE)
            if element_type not in ELEMENT_TYPES:
                continue

            connectivity = ELEMENT_TYPES[element_type].connectivity
            if connectivity == ConnectivityLevel.ALWAYS or (
                connectivity == ConnectivityLevel.ADVANCED and advanced_mode
            ):
                result.append(subentry.title)

        return result

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None

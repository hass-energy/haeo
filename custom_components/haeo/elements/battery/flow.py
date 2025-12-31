"""Battery element configuration flows."""

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
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import EntityMetadata, extract_entity_metadata
from custom_components.haeo.schema.util import UnitSpec

from .schema import (
    CONF_CAPACITY,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    DEFAULTS,
    ELEMENT_TYPE,
    BatteryConfigSchema,
)

# Unit specifications
POWER_UNITS: UnitSpec = UnitOfPower
ENERGY_UNITS: UnitSpec = UnitOfEnergy
PERCENTAGE_UNITS: list[UnitSpec] = ["%"]
PRICE_UNITS: list[UnitSpec] = [("*", "/", unit.value) for unit in UnitOfEnergy]


def _filter_incompatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that are NOT compatible with the accepted units."""
    return [v.entity_id for v in entity_metadata if not v.is_compatible_with(accepted_units)]


def _build_connection_selector(participants: list[str], current_value: str | None = None) -> vol.All:
    """Build a selector for choosing connection target from participants."""
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
    """Build the voluptuous schema for battery configuration."""
    incompatible_power = _filter_incompatible_entities(entity_metadata, POWER_UNITS)
    incompatible_energy = _filter_incompatible_entities(entity_metadata, ENERGY_UNITS)
    incompatible_percentage = _filter_incompatible_entities(entity_metadata, PERCENTAGE_UNITS)
    incompatible_price = _filter_incompatible_entities(entity_metadata, PRICE_UNITS)

    return vol.Schema(
        {
            # Required fields
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_CONNECTION): _build_connection_selector(participants, current_connection),
            vol.Required(CONF_CAPACITY): vol.All(
                EntitySelector(
                    EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        multiple=True,
                        exclude_entities=incompatible_energy,
                    )
                ),
                vol.Length(min=1, msg="At least one entity is required"),
            ),
            vol.Required(CONF_INITIAL_CHARGE_PERCENTAGE): vol.All(
                EntitySelector(
                    EntitySelectorConfig(
                        domain=["sensor", "input_number"],
                        multiple=True,
                        exclude_entities=incompatible_percentage,
                    )
                ),
                vol.Length(min=1, msg="At least one entity is required"),
            ),
            # Optional percentages with defaults
            vol.Optional(CONF_MIN_CHARGE_PERCENTAGE): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=100.0, step=0.1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(CONF_MAX_CHARGE_PERCENTAGE): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=100.0, step=0.1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(CONF_EFFICIENCY): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=100.0, step=0.1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            # Optional power limits
            vol.Optional(CONF_MAX_CHARGE_POWER): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_power,
                )
            ),
            vol.Optional(CONF_MAX_DISCHARGE_POWER): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_power,
                )
            ),
            # Optional prices
            vol.Optional(CONF_EARLY_CHARGE_INCENTIVE): NumberSelector(
                NumberSelectorConfig(min=0.0, max=1.0, step=0.001, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(CONF_DISCHARGE_COST): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_price,
                )
            ),
            # Advanced: undercharge/overcharge regions
            vol.Optional(CONF_UNDERCHARGE_PERCENTAGE): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=100.0, step=0.1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(CONF_OVERCHARGE_PERCENTAGE): NumberSelector(
                NumberSelectorConfig(
                    min=0.0, max=100.0, step=0.1, mode=NumberSelectorMode.SLIDER, unit_of_measurement="%"
                )
            ),
            vol.Optional(CONF_UNDERCHARGE_COST): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_price,
                )
            ),
            vol.Optional(CONF_OVERCHARGE_COST): EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "input_number"],
                    multiple=True,
                    exclude_entities=incompatible_price,
                )
            ),
        }
    )


class BatterySubentryFlowHandler(ConfigSubentryFlow):
    """Handle battery element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new battery element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("BatteryConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        entity_metadata = extract_entity_metadata(self.hass)
        participants = self._get_participant_names()
        schema = _build_schema(entity_metadata, participants)
        schema = self.add_suggested_values_to_schema(schema, DEFAULTS)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing battery element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("BatteryConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
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
        """Return element names available as connection targets."""
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
            if connectivity == ConnectivityLevel.ALWAYS.value or (
                connectivity == ConnectivityLevel.ADVANCED.value and advanced_mode
            ):
                result.append(subentry.title)

        return result

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None

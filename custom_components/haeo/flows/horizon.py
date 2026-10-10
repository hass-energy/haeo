"""Planning horizon field shared by the hub setup and options forms."""

from collections.abc import Mapping
from typing import Any  # noqa: TID251  # Selector.__call__ is Any-typed upstream

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.selector import (
    ChooseSelector,
    ChooseSelectorChoiceConfig,
    ChooseSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_HORIZON, HORIZON_PRESET_5_DAYS, HORIZON_PRESET_DAYS
from custom_components.haeo.core.data.forecast_times import forecast_boundaries
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.horizon_value import (
    HorizonValue,
    as_horizon_preset_value,
    is_horizon_preset_value,
)

CHOICE_PRESET = "preset"
CHOICE_ENTITY = "entity"


class HorizonSelector(ChooseSelector):  # type: ignore[type-arg]
    """Choose a horizon preset or a forecast entity, returning the stored horizon value."""

    def __call__(self, data: Any) -> HorizonValue:  # matches upstream Selector.__call__(self, data: Any) signature
        """Validate the selection and convert it to a horizon value."""
        value = str(super().__call__(data))  # type: ignore[misc]  # ChooseSelector is generic upstream without a usable type argument
        if isinstance(data, Mapping):
            choice = data["active_choice"]
        else:
            choice = CHOICE_PRESET if value in HORIZON_PRESET_DAYS else CHOICE_ENTITY
        if choice == CHOICE_PRESET:
            return as_horizon_preset_value(value)
        return as_entity_value([value])


def horizon_field(current: HorizonValue | None = None) -> tuple[vol.Required, HorizonSelector]:
    """Return the schema entry for the planning horizon, defaulting to the current horizon.

    The current horizon's choice is listed first, because Home Assistant only
    applies a default to the first choice.
    """
    current = current or as_horizon_preset_value(HORIZON_PRESET_5_DAYS)
    preset_choice = ChooseSelectorChoiceConfig(
        selector=SelectSelector(
            SelectSelectorConfig(
                options=list(HORIZON_PRESET_DAYS),
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="horizon_preset",
            )
        ).serialize()["selector"]
    )
    entity_choice = ChooseSelectorChoiceConfig(
        selector=EntitySelector(EntitySelectorConfig(domain="sensor")).serialize()["selector"]
    )
    if is_horizon_preset_value(current):
        choices = {CHOICE_PRESET: preset_choice, CHOICE_ENTITY: entity_choice}
        default = current["value"]
    else:
        choices = {CHOICE_ENTITY: entity_choice, CHOICE_PRESET: preset_choice}
        default = current["value"][0]
    selector = HorizonSelector(ChooseSelectorConfig(choices=choices, translation_key="horizon_source"))
    return vol.Required(CONF_HORIZON, default=default), selector


def validate_horizon(hass: HomeAssistant, horizon: HorizonValue, errors: dict[str, str], entry_id: str | None) -> None:
    """Add an error when a horizon entity cannot provide the horizon.

    The entity must currently report a forecast of at least two increasing
    times. It cannot belong to this hub, because the hub's sensors are
    computed on its horizon.
    """
    if is_horizon_preset_value(horizon):
        return
    entity_id = horizon["value"][0]
    registry_entry = er.async_get(hass).async_get(entity_id)
    if entry_id is not None and registry_entry is not None and registry_entry.config_entry_id == entry_id:
        errors[CONF_HORIZON] = "horizon_entity_from_this_hub"
        return
    state = hass.states.get(entity_id)
    if state is None:
        errors[CONF_HORIZON] = "horizon_entity_invalid"
        return
    try:
        forecast_boundaries(state)
    except ValueError:
        errors[CONF_HORIZON] = "horizon_entity_invalid"


__all__ = ["HorizonSelector", "horizon_field", "validate_horizon"]

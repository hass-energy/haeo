"""Config flow helpers for hub planning horizon ChooseSelector."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.selector import (
    ChooseSelectorChoiceConfig,
    ChooseSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.const import DOMAIN, OUTPUT_NAME_HORIZON
from custom_components.haeo.core.const import (
    CONF_HORIZON,
    CONF_HORIZON_PRESET,
    HORIZON_PRESET_5_DAYS,
    HUB_SECTION_COMMON,
)
from custom_components.haeo.core.data.forecast_times import extract_haeo_forecast_timestamps
from custom_components.haeo.core.data.loader.extractors import haeo as haeo_extractor
from custom_components.haeo.core.schema import (
    as_entity_value,
    as_horizon_preset_value,
    is_horizon_entity_value,
    is_horizon_preset_value,
)
from custom_components.haeo.flows.field_schema import NormalizingChooseSelector
from custom_components.haeo.horizon import _HassStateAdapter

HORIZON_PRESET_OPTIONS_UI: list[str] = ["2_days", "3_days", "5_days", "7_days"]

CHOICE_PRESET = "preset"
CHOICE_ENTITY = "entity"


class HorizonChooseSelector(NormalizingChooseSelector):  # type: ignore[type-arg]
    """ChooseSelector for planning horizon preset vs entity sources."""

    def __call__(self, data: Any) -> Any:
        """Normalize choose selector submissions to preset or entity values."""
        if isinstance(data, dict) and "active_choice" in data:
            choice = data.get("active_choice")
            if choice == CHOICE_PRESET:
                return data.get(CHOICE_PRESET, HORIZON_PRESET_5_DAYS)
            if choice == CHOICE_ENTITY:
                entity = data.get(CHOICE_ENTITY)
                if isinstance(entity, str):
                    return entity
                if isinstance(entity, list):
                    return entity
        return super().__call__(data)  # type: ignore[misc]


def build_horizon_choose_selector(
    *,
    preferred_choice: str = CHOICE_PRESET,
) -> HorizonChooseSelector:
    """Build the planning horizon ChooseSelector with preset first by default."""
    preset_selector = SelectSelector(
        SelectSelectorConfig(
            options=HORIZON_PRESET_OPTIONS_UI,
            mode=SelectSelectorMode.DROPDOWN,
            translation_key="horizon_preset",
        )
    )
    entity_selector = EntitySelector(
        EntitySelectorConfig(
            domain=["sensor"],
            multiple=False,
        )
    )
    choice_map = {
        CHOICE_PRESET: ChooseSelectorChoiceConfig(selector=preset_selector.serialize()["selector"]),
        CHOICE_ENTITY: ChooseSelectorChoiceConfig(selector=entity_selector.serialize()["selector"]),
    }
    choice_order = [CHOICE_PRESET, CHOICE_ENTITY]
    if preferred_choice in choice_order:
        choice_order.remove(preferred_choice)
        choice_order.insert(0, preferred_choice)

    return HorizonChooseSelector(
        ChooseSelectorConfig(
            choices={key: choice_map[key] for key in choice_order},
            translation_key="horizon_source",
        )
    )


def get_horizon_preferred_choice(common_data: Mapping[str, Any] | None) -> str:
    """Return which choose branch should appear first for reconfigure."""
    if common_data is None:
        return CHOICE_PRESET
    horizon = common_data.get(CONF_HORIZON)
    if is_horizon_entity_value(horizon):
        return CHOICE_ENTITY
    return CHOICE_PRESET


def horizon_config_to_form_default(common_data: Mapping[str, Any] | None) -> Any:
    """Convert stored horizon config to a form default for the nested selector."""
    if common_data is None:
        return HORIZON_PRESET_5_DAYS

    horizon = common_data.get(CONF_HORIZON)
    if is_horizon_entity_value(horizon):
        entities = horizon["value"]
        return entities[0] if entities else ""
    if is_horizon_preset_value(horizon):
        return horizon["value"]

    legacy = common_data.get(CONF_HORIZON_PRESET)
    if isinstance(legacy, str) and legacy:
        return legacy
    return HORIZON_PRESET_5_DAYS


def preprocess_horizon_input(value: Any) -> Any:
    """Normalize raw ChooseSelector dict submissions for horizon."""
    if isinstance(value, dict) and "active_choice" in value:
        choice = value.get("active_choice")
        if choice == CHOICE_PRESET:
            return value.get(CHOICE_PRESET, HORIZON_PRESET_5_DAYS)
        if choice == CHOICE_ENTITY:
            entity = value.get(CHOICE_ENTITY)
            if isinstance(entity, str):
                return entity
            if isinstance(entity, list) and entity:
                return entity[0]
            return ""
    return value


def horizon_input_to_config(value: Any) -> dict[str, Any]:
    """Convert processed horizon form value to stored schema config."""
    if isinstance(value, list):
        if not value:
            msg = "Horizon entity is required"
            raise vol.Invalid(msg)
        return as_entity_value(value if isinstance(value[0], str) else [str(v) for v in value])
    if isinstance(value, str):
        if value.startswith(("sensor.", f"{DOMAIN}.")):
            return as_entity_value([value])
        return as_horizon_preset_value(value)
    msg = "Invalid horizon configuration"
    raise vol.Invalid(msg)


def validate_horizon_entity(
    hass: HomeAssistant,
    entity_id: str,
    *,
    config_entry: ConfigEntry | None = None,
) -> None:
    """Validate that an entity provides a HAEO-format forecast for horizon use."""
    if config_entry is not None:
        from homeassistant.helpers import entity_registry as er  # noqa: PLC0415

        unique_id = f"{config_entry.entry_id}_{OUTPUT_NAME_HORIZON}"
        own_horizon = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id == own_horizon:
            msg = "Cannot use the HAEO horizon sensor as the horizon source"
            raise vol.Invalid(msg)

    state = hass.states.get(entity_id)
    if state is None:
        msg = f"Entity {entity_id} is not available"
        raise vol.Invalid(msg)

    adapter = _HassStateAdapter(state.entity_id, state.state, state.attributes)
    if not haeo_extractor.Parser.detect(adapter):
        msg = f"Entity {entity_id} must provide a HAEO-format forecast attribute"
        raise vol.Invalid(msg)

    try:
        extract_haeo_forecast_timestamps(adapter)
    except ValueError as exc:
        raise vol.Invalid(str(exc)) from exc


def is_horizon_entity_selection(value: Any) -> bool:
    """Return True if processed horizon input selects entity mode."""
    processed = preprocess_horizon_input(value)
    if isinstance(processed, list):
        return bool(processed)
    return isinstance(processed, str) and processed.startswith(("sensor.", f"{DOMAIN}."))


def get_horizon_preset_from_input(user_input: Mapping[str, Any]) -> str | None:
    """Extract preset key from user input common section after preprocessing."""
    common = user_input.get(HUB_SECTION_COMMON, {})
    if not isinstance(common, Mapping):
        return None
    raw = common.get(CONF_HORIZON)
    processed = preprocess_horizon_input(raw)
    if isinstance(processed, str) and not processed.startswith("sensor."):
        return processed
    return None


def stored_horizon_from_common(common: Mapping[str, Any]) -> dict[str, Any]:
    """Return stored horizon schema value from common section input."""
    raw = common.get(CONF_HORIZON)
    processed = preprocess_horizon_input(raw)
    return horizon_input_to_config(processed)


__all__ = [
    "CHOICE_ENTITY",
    "CHOICE_PRESET",
    "HorizonChooseSelector",
    "build_horizon_choose_selector",
    "get_horizon_preferred_choice",
    "get_horizon_preset_from_input",
    "horizon_config_to_form_default",
    "horizon_input_to_config",
    "is_horizon_entity_selection",
    "preprocess_horizon_input",
    "stored_horizon_from_common",
    "validate_horizon_entity",
]

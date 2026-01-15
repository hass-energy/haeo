"""Shared utilities and mixin for element subentry config flows.

This module provides:
- get_unit_spec_for_output_type(): Map OutputType to UnitSpec for entity filtering
- build_inclusion_map(): Generate field → compatible entities mapping from INPUT_FIELDS
- filter_compatible_entities(): Filter entity metadata by unit compatibility
- build_participant_selector(): Create dropdown selector for element names
- ElementFlowMixin: Mixin providing common subentry flow functionality
"""

from typing import Any, ClassVar, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.helpers.selector import SelectOptionDict, SelectSelector, SelectSelectorConfig, SelectSelectorMode
import voluptuous as vol

from custom_components.haeo.const import CONF_ADVANCED_MODE, CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import EntityMetadata
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.schema.util import UnitSpec

# Price unit pattern: matches any currency divided by energy unit ($/kWh, €/MWh, etc.)
PRICE_UNIT_SPEC: Final[list[UnitSpec]] = [("*", "/", unit.value) for unit in UnitOfEnergy]


def get_unit_spec_for_output_type(output_type: OutputType) -> UnitSpec | list[UnitSpec] | None:
    """Map OutputType to the appropriate UnitSpec for entity filtering.

    Args:
        output_type: The output type from InputFieldInfo.

    Returns:
        UnitSpec for filtering compatible entities, or None if no filtering needed.

    """
    match output_type:
        case OutputType.POWER | OutputType.POWER_FLOW:
            return UnitOfPower
        case OutputType.POWER_LIMIT:
            return UnitOfPower
        case OutputType.ENERGY:
            return UnitOfEnergy
        case OutputType.STATE_OF_CHARGE | OutputType.EFFICIENCY:
            return [PERCENTAGE]
        case OutputType.PRICE:
            return PRICE_UNIT_SPEC
        case _:
            # STATUS, COST, DURATION, SHADOW_PRICE - no unit filtering
            return None


def filter_compatible_entities(
    entity_metadata: list[EntityMetadata],
    accepted_units: UnitSpec | list[UnitSpec],
) -> list[str]:
    """Return entity IDs that ARE compatible with the accepted units.

    Args:
        entity_metadata: List of entity metadata from extract_entity_metadata.
        accepted_units: UnitSpec or list of UnitSpecs to match against.

    Returns:
        List of entity IDs that should be included in selection.

    """
    return [v.entity_id for v in entity_metadata if v.is_compatible_with(accepted_units)]


def build_inclusion_map(
    input_fields: tuple[InputFieldInfo[Any], ...],
    entity_metadata: list[EntityMetadata],
) -> dict[str, list[str]]:
    """Build field name → compatible entity IDs mapping from INPUT_FIELDS.

    This dynamically generates the inclusion map by looking up each field's
    output_type and computing which entities are compatible.

    Args:
        input_fields: Tuple of InputFieldInfo from element's schema.
        entity_metadata: List of entity metadata from extract_entity_metadata.

    Returns:
        Dict mapping field names to lists of entity IDs to include.

    """
    result: dict[str, list[str]] = {}

    for field_info in input_fields:
        unit_spec = get_unit_spec_for_output_type(field_info.output_type)
        if unit_spec is not None:
            result[field_info.field_name] = filter_compatible_entities(entity_metadata, unit_spec)

    return result


def build_participant_selector(
    participants: list[str],
    current_value: str | None = None,
) -> vol.All:
    """Build a selector for choosing element names from available participants.

    Args:
        participants: List of available element names.
        current_value: Current value to preserve if not in participants list.

    Returns:
        Voluptuous validator with SelectSelector.

    """
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


class ElementFlowMixin:
    """Mixin providing common element subentry flow functionality.

    This mixin provides shared methods for all element config flows:
    - Name validation and duplicate checking
    - Participant name retrieval based on connectivity level
    - Subentry ID retrieval for reconfigure flows

    Expected attributes on the class using this mixin:
    - hass: HomeAssistant instance
    - _get_entry(): Returns the parent ConfigEntry
    - _get_reconfigure_subentry(): Returns the subentry being reconfigured
    - context: Flow context dict (from ConfigSubentryFlow)

    Class variables that can be set by subclasses:
    - has_value_source_step: Whether the flow uses a separate step for value sources

    """

    # Class variable indicating whether this flow uses a separate value source step
    has_value_source_step: ClassVar[bool] = False

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry.

        Used to validate that a new element name doesn't conflict with existing ones.

        Returns:
            Set of element names currently in use.

        """
        current_id = self._get_current_subentry_id()
        entry: ConfigEntry = self._get_entry()  # type: ignore[attr-defined]
        return {subentry.title for subentry in entry.subentries.values() if subentry.subentry_id != current_id}

    def _get_participant_names(self) -> list[str]:
        """Return element names available as connection endpoints.

        Filters elements based on their connectivity level and the hub's
        advanced mode setting.

        Returns:
            List of element names that can be used as connection targets.

        """
        from custom_components.haeo.elements import ELEMENT_TYPES, ConnectivityLevel  # noqa: PLC0415

        hub_entry: ConfigEntry = self._get_entry()  # type: ignore[attr-defined]
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
        """Return the active subentry ID when reconfiguring, otherwise None.

        Uses the flow context to determine if we're in a reconfigure flow.

        Returns:
            Subentry ID if reconfiguring, None otherwise.

        """
        context: dict[str, Any] = getattr(self, "context", {})
        subentry_id = context.get("subentry_id")
        return subentry_id if isinstance(subentry_id, str) else None

    def _validate_name(self, name: str | None, errors: dict[str, str]) -> bool:
        """Validate an element name and add errors if invalid.

        Args:
            name: The name to validate.
            errors: Dict to add error messages to.

        Returns:
            True if name is valid, False otherwise.

        """
        if not name:
            errors[CONF_NAME] = "missing_name"
            return False
        if name in self._get_used_names():
            errors[CONF_NAME] = "name_exists"
            return False
        return True


__all__ = [
    "ElementFlowMixin",
    "build_inclusion_map",
    "build_participant_selector",
    "filter_compatible_entities",
    "get_unit_spec_for_output_type",
]

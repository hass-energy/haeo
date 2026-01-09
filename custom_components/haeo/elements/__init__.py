"""HAEO element registry with explicit per-element adapters.

This module provides a centralized registry for all element types and their adapters.
The adapter layer transforms configuration elements into model elements and maps
model outputs to user-friendly device outputs.

Adapter Pattern:
    Configuration Element (with entity IDs) →
    Adapter.load() →
    Configuration Data (with loaded values) →
    Adapter.model_elements() →
    Model Elements (pure optimization) →
    Model.optimize() →
    Model Outputs (element-agnostic) →
    Adapter.outputs() →
    Device Outputs (user-friendly sensors)

Sub-element Naming Convention:
    Adapters may create multiple model elements and devices from a single config element.
    Sub-elements follow the pattern: {main_element}:{subname}
    Example: Battery "home_battery" creates:
        - "home_battery" (aggregate device)
        - "home_battery:undercharge" (undercharge region device)
        - "home_battery:normal" (normal region device)
        - "home_battery:overcharge" (overcharge region device)
        - "home_battery:connection" (implicit connection to network)
"""

from collections.abc import Mapping, Sequence
import logging
import types
from typing import (
    Any,
    Final,
    Literal,
    NamedTuple,
    Protocol,
    TypeGuard,
    get_args,
    get_origin,
    get_type_hints,
    runtime_checkable,
)

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import (
    CONF_ELEMENT_TYPE,
    NETWORK_OUTPUT_NAMES,
    ConnectivityLevel,
    NetworkDeviceName,
    NetworkOutputName,
)
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData

from . import battery, battery_section, connection, grid, inverter, load, node, solar
from .input_fields import InputFieldInfo

_LOGGER = logging.getLogger(__name__)

type ElementType = Literal[
    "battery",
    "battery_section",
    "connection",
    "solar",
    "grid",
    "inverter",
    "load",
    "node",
]

ELEMENT_TYPE_INVERTER: Final = inverter.ELEMENT_TYPE
ELEMENT_TYPE_BATTERY: Final = battery.ELEMENT_TYPE
ELEMENT_TYPE_BATTERY_SECTION: Final = battery_section.ELEMENT_TYPE
ELEMENT_TYPE_CONNECTION: Final = connection.ELEMENT_TYPE
ELEMENT_TYPE_SOLAR: Final = solar.ELEMENT_TYPE
ELEMENT_TYPE_GRID: Final = grid.ELEMENT_TYPE
ELEMENT_TYPE_LOAD: Final = load.ELEMENT_TYPE
ELEMENT_TYPE_NODE: Final = node.ELEMENT_TYPE

ElementConfigSchema = (
    inverter.InverterConfigSchema
    | battery.BatteryConfigSchema
    | battery_section.BatterySectionConfigSchema
    | grid.GridConfigSchema
    | load.LoadConfigSchema
    | solar.SolarConfigSchema
    | node.NodeConfigSchema
    | connection.ConnectionConfigSchema
)

ElementConfigData = (
    inverter.InverterConfigData
    | battery.BatteryConfigData
    | battery_section.BatterySectionConfigData
    | grid.GridConfigData
    | load.LoadConfigData
    | solar.SolarConfigData
    | node.NodeConfigData
    | connection.ConnectionConfigData
)


type ElementOutputName = (
    inverter.InverterOutputName
    | battery.BatteryOutputName
    | battery_section.BatterySectionOutputName
    | connection.ConnectionOutputName
    | grid.GridOutputName
    | load.LoadOutputName
    | node.NodeOutputName
    | solar.SolarOutputName
    | NetworkOutputName
)

ELEMENT_OUTPUT_NAMES: Final[frozenset[ElementOutputName]] = frozenset(
    inverter.INVERTER_OUTPUT_NAMES
    | battery.BATTERY_OUTPUT_NAMES
    | battery_section.BATTERY_SECTION_OUTPUT_NAMES
    | connection.CONNECTION_OUTPUT_NAMES
    | grid.GRID_OUTPUT_NAMES
    | load.LOAD_OUTPUT_NAMES
    | node.NODE_OUTPUT_NAMES
    | solar.SOLAR_OUTPUT_NAMES
    | NETWORK_OUTPUT_NAMES
)

# Device translation keys for devices
# These are the translation keys used for devices created by adapters
type ElementDeviceName = (
    inverter.InverterDeviceName
    | battery.BatteryDeviceName
    | battery_section.BatterySectionDeviceName
    | connection.ConnectionDeviceName
    | grid.GridDeviceName
    | load.LoadDeviceName
    | node.NodeDeviceName
    | solar.SolarDeviceName
    | NetworkDeviceName
)

NETWORK_DEVICE_NAMES: Final[frozenset[NetworkDeviceName]] = frozenset(("network",))

ELEMENT_DEVICE_NAMES: Final[frozenset[ElementDeviceName]] = frozenset(
    inverter.INVERTER_DEVICE_NAMES
    | battery.BATTERY_DEVICE_NAMES
    | battery_section.BATTERY_SECTION_DEVICE_NAMES
    | connection.CONNECTION_DEVICE_NAMES
    | grid.GRID_DEVICE_NAMES
    | load.LOAD_DEVICE_NAMES
    | node.NODE_DEVICE_NAMES
    | solar.SOLAR_DEVICE_NAMES
    | NETWORK_DEVICE_NAMES
)


@runtime_checkable
class ElementAdapter(Protocol):
    """Protocol for element adapters.

    Each element type provides an adapter that bridges Home Assistant
    configuration with the LP model layer. Adapters must implement this
    protocol and be registered in the ELEMENT_TYPES registry.

    Note: Attributes are defined as read-only properties in the Protocol,
    but implementations use class attributes with Final for immutability.
    """

    element_type: str
    """The element type identifier."""

    flow_class: type
    """The config flow handler class for this element type."""

    advanced: bool
    """Whether this element type requires advanced mode."""

    connectivity: ConnectivityLevel
    """Visibility level in connection selectors."""

    def available(self, config: Any, *, hass: HomeAssistant, **kwargs: Any) -> bool:
        """Check if element configuration can be loaded."""
        ...

    async def load(
        self,
        config: Any,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> Any:
        """Load configuration values from sensors."""
        ...

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: Any,
    ) -> Any:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (e.g., connection)

        Returns:
            ConfigData with all fields populated and defaults applied

        """
        ...

    def model_elements(self, config: Any) -> list[dict[str, Any]]:
        """Return model element parameters for the loaded config."""
        ...

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: Any,
    ) -> Mapping[Any, Mapping[Any, OutputData]]:
        """Map model outputs to device-specific outputs."""
        ...


ELEMENT_TYPES: dict[ElementType, ElementAdapter] = {
    grid.ELEMENT_TYPE: grid.adapter,
    load.ELEMENT_TYPE: load.adapter,
    inverter.ELEMENT_TYPE: inverter.adapter,
    solar.ELEMENT_TYPE: solar.adapter,
    battery.ELEMENT_TYPE: battery.adapter,
    connection.ELEMENT_TYPE: connection.adapter,
    node.ELEMENT_TYPE: node.adapter,
    battery_section.ELEMENT_TYPE: battery_section.adapter,
}


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


# Map element types to their ConfigSchema TypedDict classes for reflection
# Typed with ElementType keys to enable type-safe indexing after is_element_type check
ELEMENT_CONFIG_SCHEMAS: Final[dict[ElementType, type]] = {
    "battery": battery.BatteryConfigSchema,
    "battery_section": battery_section.BatterySectionConfigSchema,
    "connection": connection.ConnectionConfigSchema,
    "grid": grid.GridConfigSchema,
    "inverter": inverter.InverterConfigSchema,
    "load": load.LoadConfigSchema,
    "node": node.NodeConfigSchema,
    "solar": solar.SolarConfigSchema,
}


def is_element_type(value: Any) -> TypeGuard[ElementType]:
    """Return True when value is a valid ElementType literal.

    Use this to narrow Any values (e.g., from dict.get()) to ElementType,
    enabling type-safe access to ELEMENT_TYPES and ELEMENT_CONFIG_SCHEMAS.
    """
    return value in ELEMENT_TYPES


def _conforms_to_typed_dict(value: Mapping[str, Any], typed_dict_cls: type) -> bool:
    """Check if a mapping conforms to a TypedDict's required fields and types.

    Uses reflection to get required keys and type hints from the TypedDict class.
    Only checks required fields (not NotRequired fields).
    """
    # Get required keys from TypedDict
    required_keys: frozenset[str] = getattr(typed_dict_cls, "__required_keys__", frozenset())

    # Get type hints for the TypedDict
    hints = get_type_hints(typed_dict_cls)

    for key in required_keys:
        if key not in value:
            return False

        # Required keys in a TypedDict always have type hints
        expected_type = hints[key]

        # Get the origin type for generic types (e.g., list[str] -> list)
        origin = get_origin(expected_type)
        check_type = origin if origin is not None else expected_type

        # Handle Literal types by checking if value is one of the allowed values
        # For Literal, we don't do isinstance check - just ensure the field exists
        if check_type is not Literal:
            if check_type is types.UnionType:
                # Handle union types (e.g., list[str] | float)
                # Use the origin for generic args (e.g., list[str] -> list); for primitive
                # types (e.g., float, int) get_origin() returns None so we fall back to arg
                # itself, producing a tuple like (list, float) suitable for isinstance().
                union_args = get_args(expected_type)
                allowed_types = tuple(get_origin(arg) or arg for arg in union_args)
                if not isinstance(value[key], allowed_types):
                    return False
            elif not isinstance(value[key], check_type):
                return False

    return True


def is_element_config_schema(value: Any) -> TypeGuard[ElementConfigSchema]:
    """Return True when value matches any ElementConfigSchema TypedDict.

    Performs structural validation using reflection - checks that:
    - value is a mapping
    - has a valid element_type field
    - has all required fields for that element type (from TypedDict __required_keys__)
    - all required fields have the correct type (from TypedDict type hints)
    """
    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        return False

    # Get the TypedDict class - type-safe because is_element_type narrowed element_type
    schema_cls = ELEMENT_CONFIG_SCHEMAS[element_type]

    return _conforms_to_typed_dict(value, schema_cls)


def collect_element_subentries(entry: ConfigEntry) -> list[ValidatedElementSubentry]:
    """Return validated element subentries excluding the network element."""
    result: list[ValidatedElementSubentry] = []

    for subentry in entry.subentries.values():
        if subentry.subentry_type not in ELEMENT_TYPES:
            # Not an element type (e.g., network) - skip silently
            continue

        if not is_element_config_schema(subentry.data):
            # Element type but failed validation - log warning
            _LOGGER.warning(
                "Subentry '%s' (type=%s) failed config validation and will be excluded. Data: %s",
                subentry.title,
                subentry.subentry_type,
                dict(subentry.data),
            )
            continue

        result.append(
            ValidatedElementSubentry(
                name=subentry.title,
                element_type=subentry.data[CONF_ELEMENT_TYPE],
                subentry=subentry,
                config=subentry.data,
            )
        )

    return result


# Registry mapping element types to their input field definitions
_INPUT_FIELDS_REGISTRY: Final[dict[str, tuple[InputFieldInfo[Any], ...]]] = {
    battery.ELEMENT_TYPE: battery.INPUT_FIELDS,
    grid.ELEMENT_TYPE: grid.INPUT_FIELDS,
    solar.ELEMENT_TYPE: solar.INPUT_FIELDS,
    load.ELEMENT_TYPE: load.INPUT_FIELDS,
    inverter.ELEMENT_TYPE: inverter.INPUT_FIELDS,
    connection.ELEMENT_TYPE: connection.INPUT_FIELDS,
    node.ELEMENT_TYPE: node.INPUT_FIELDS,
}


def get_input_fields(element_type: str) -> tuple[InputFieldInfo[Any], ...]:
    """Return input field definitions for an element type.

    Args:
        element_type: The element type (e.g., "battery", "grid")

    Returns:
        Tuple of InputFieldInfo for fields that should become input entities.
        Returns empty tuple for unknown element types.

    """
    return _INPUT_FIELDS_REGISTRY.get(element_type, ())


__all__ = [
    "ELEMENT_CONFIG_SCHEMAS",
    "ELEMENT_DEVICE_NAMES",
    "ELEMENT_TYPES",
    "ELEMENT_TYPE_BATTERY",
    "ELEMENT_TYPE_BATTERY_SECTION",
    "ELEMENT_TYPE_CONNECTION",
    "ELEMENT_TYPE_GRID",
    "ELEMENT_TYPE_INVERTER",
    "ELEMENT_TYPE_LOAD",
    "ELEMENT_TYPE_NODE",
    "ELEMENT_TYPE_SOLAR",
    "ConnectivityLevel",
    "ElementAdapter",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementDeviceName",
    "ElementType",
    "InputFieldInfo",
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "get_input_fields",
    "is_element_config_schema",
    "is_element_type",
]

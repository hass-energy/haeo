"""HAEO element registry with explicit per-element adapters.

This module provides a centralized registry for all element types and their adapters.
The adapter layer transforms configuration elements into model elements and maps
model outputs to user-friendly device outputs.

Adapter Pattern:
    Configuration Element (with entity IDs) →
    Adapter.load() →
    Configuration Data (with loaded values) →
    Adapter.create_model_elements() →
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

from collections.abc import Awaitable, Callable, Mapping
import enum
import logging
from typing import Any, Final, Literal, NamedTuple, TypeGuard, cast

from homeassistant.config_entries import ConfigEntry, ConfigSubentry, ConfigSubentryFlow

from custom_components.haeo.const import CONF_ELEMENT_TYPE, NETWORK_OUTPUT_NAMES, NetworkDeviceName, NetworkOutputName
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData

from . import battery, battery_section, connection, grid, inverter, load, node, solar

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
    | connection.PowerConnectionOutputName
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

type CreateModelElementsFn = Callable[[Any], list[dict[str, Any]]]

type OutputsFn = Callable[
    [str, Mapping[str, Mapping[ModelOutputName, OutputData]], Any],
    Mapping[ElementDeviceName, Mapping[ElementOutputName, OutputData]],
]

type AvailableFn = Callable[..., bool]

type LoadFn = Callable[..., Awaitable[Any]]


class ConnectivityLevel(enum.Enum):
    """Connectivity level for element types in connection selectors.

    - ALWAYS: Always shown in connection selectors
    - ADVANCED: Only shown when advanced mode is enabled
    - NEVER: Never shown in connection selectors
    """

    ALWAYS = "always"
    ADVANCED = "advanced"
    NEVER = "never"


class ElementRegistryEntry(NamedTuple):
    """Registry entry for an element type.

    Each element type provides:
        - flow_class: ConfigSubentryFlow subclass for add/reconfigure UI
        - available(config, *, hass) -> bool: Check if sensors are available
        - load(config, *, hass, forecast_times) -> ConfigData: Load sensor values
        - create_model_elements(config) -> list[dict]: Create model elements
        - outputs(name, model_outputs, config) -> dict: Map model outputs to devices

    The advanced flag indicates whether this element type is only shown when
    advanced mode is enabled on the hub.

    The connectivity field indicates when this element type appears in connection
    selectors:
        - ALWAYS: Always shown in connection selectors
        - ADVANCED: Only shown when advanced mode is enabled
        - NEVER: Never shown in connection selectors
    """

    flow_class: type[ConfigSubentryFlow]
    available: AvailableFn
    load: LoadFn
    create_model_elements: CreateModelElementsFn
    outputs: OutputsFn
    translation_key: ElementType
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER


ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    grid.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=grid.GridSubentryFlowHandler,
        available=grid.available,
        load=grid.load,
        create_model_elements=grid.create_model_elements,
        outputs=cast("OutputsFn", grid.outputs),
        translation_key=grid.ELEMENT_TYPE,
        connectivity=ConnectivityLevel.ADVANCED,
    ),
    load.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=load.LoadSubentryFlowHandler,
        available=load.available,
        load=load.load,
        create_model_elements=load.create_model_elements,
        outputs=cast("OutputsFn", load.outputs),
        translation_key=load.ELEMENT_TYPE,
        connectivity=ConnectivityLevel.ADVANCED,
    ),
    inverter.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=inverter.InverterSubentryFlowHandler,
        available=inverter.available,
        load=inverter.load,
        create_model_elements=inverter.create_model_elements,
        outputs=cast("OutputsFn", inverter.outputs),
        translation_key=inverter.ELEMENT_TYPE,
        connectivity=ConnectivityLevel.ALWAYS,
    ),
    solar.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=solar.SolarSubentryFlowHandler,
        available=solar.available,
        load=solar.load,
        create_model_elements=solar.create_model_elements,
        outputs=cast("OutputsFn", solar.outputs),
        translation_key=solar.ELEMENT_TYPE,
        connectivity=ConnectivityLevel.ADVANCED,
    ),
    battery.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=battery.BatterySubentryFlowHandler,
        available=battery.available,
        load=battery.load,
        create_model_elements=battery.create_model_elements,
        outputs=cast("OutputsFn", battery.outputs),
        translation_key=battery.ELEMENT_TYPE,
        connectivity=ConnectivityLevel.ADVANCED,
    ),
    connection.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=connection.ConnectionSubentryFlowHandler,
        available=connection.available,
        load=connection.load,
        create_model_elements=connection.create_model_elements,
        outputs=cast("OutputsFn", connection.outputs),
        translation_key=connection.ELEMENT_TYPE,
        advanced=True,
        connectivity=ConnectivityLevel.NEVER,
    ),
    node.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=node.NodeSubentryFlowHandler,
        available=node.available,
        load=node.load,
        create_model_elements=node.create_model_elements,
        outputs=cast("OutputsFn", node.outputs),
        translation_key=node.ELEMENT_TYPE,
        advanced=True,
        connectivity=ConnectivityLevel.ALWAYS,
    ),
    battery_section.ELEMENT_TYPE: ElementRegistryEntry(
        flow_class=battery_section.BatterySectionSubentryFlowHandler,
        available=battery_section.available,
        load=battery_section.load,
        create_model_elements=battery_section.create_model_elements,
        outputs=cast("OutputsFn", battery_section.outputs),
        translation_key=battery_section.ELEMENT_TYPE,
        advanced=True,
        connectivity=ConnectivityLevel.ALWAYS,
    ),
}


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


def is_element_config_schema(value: Any) -> TypeGuard[ElementConfigSchema]:
    """Return True when value matches any ElementConfigSchema TypedDict.

    Performs basic structural validation - checks that:
    - value is a mapping
    - has a valid element_type field
    - has a name field
    """
    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if element_type not in ELEMENT_TYPES:
        return False

    # Basic structural check: must have a name
    return "name" in value


def collect_element_subentries(entry: ConfigEntry) -> list[ValidatedElementSubentry]:
    """Return validated element subentries excluding the network element."""
    return [
        ValidatedElementSubentry(
            name=subentry.title,
            element_type=subentry.data[CONF_ELEMENT_TYPE],
            subentry=subentry,
            config=subentry.data,
        )
        for subentry in entry.subentries.values()
        if subentry.subentry_type in ELEMENT_TYPES and is_element_config_schema(subentry.data)
    ]


__all__ = [
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
    "AvailableFn",
    "ConnectivityLevel",
    "CreateModelElementsFn",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementDeviceName",
    "ElementRegistryEntry",
    "ElementType",
    "LoadFn",
    "OutputsFn",
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "is_element_config_schema",
]

"""HAEO element registry with field-based metadata.

This module provides a centralized registry for all element types and their adapters.
The adapter layer transforms configuration elements into model elements and maps
model outputs to user-friendly device outputs.

Adapter Pattern:
    Configuration Element (with entity IDs) →
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

from collections.abc import Callable, Mapping
import logging
from typing import Any, Final, Literal, NamedTuple, TypeGuard

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, NETWORK_OUTPUT_NAMES, NetworkOutputName
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.schema import schema_for_type

from . import battery, connection, grid, load, node, photovoltaics

_LOGGER = logging.getLogger(__name__)

type ElementType = Literal[
    "battery",
    "connection",
    "photovoltaics",
    "grid",
    "load",
    "node",
]

ELEMENT_TYPE_BATTERY: Final = battery.ELEMENT_TYPE
ELEMENT_TYPE_CONNECTION: Final = connection.ELEMENT_TYPE
ELEMENT_TYPE_PHOTOVOLTAICS: Final = photovoltaics.ELEMENT_TYPE
ELEMENT_TYPE_GRID: Final = grid.ELEMENT_TYPE
ELEMENT_TYPE_LOAD: Final = load.ELEMENT_TYPE
ELEMENT_TYPE_NODE: Final = node.ELEMENT_TYPE

ElementConfigSchema = (
    battery.BatteryConfigSchema
    | grid.GridConfigSchema
    | load.LoadConfigSchema
    | photovoltaics.PhotovoltaicsConfigSchema
    | node.NodeConfigSchema
    | connection.ConnectionConfigSchema
)

ElementConfigData = (
    battery.BatteryConfigData
    | grid.GridConfigData
    | load.LoadConfigData
    | photovoltaics.PhotovoltaicsConfigData
    | node.NodeConfigData
    | connection.ConnectionConfigData
)


type ElementOutputName = (
    battery.BatteryOutputName
    | connection.ConnectionOutputName
    | grid.GridOutputName
    | load.LoadOutputName
    | node.NodeOutputName
    | photovoltaics.PhotovoltaicsOutputName
    | NetworkOutputName
)

ELEMENT_OUTPUT_NAMES: Final[frozenset[ElementOutputName]] = frozenset(
    battery.BATTERY_OUTPUT_NAMES
    | connection.CONNECTION_OUTPUT_NAMES
    | grid.GRID_OUTPUT_NAMES
    | load.LOAD_OUTPUT_NAMES
    | node.NODE_OUTPUT_NAMES
    | photovoltaics.PHOTOVOLTAIC_OUTPUT_NAMES
    | NETWORK_OUTPUT_NAMES
)

type CreateModelElementsFn = Callable[[Any], list[dict[str, Any]]]

type OutputsFn = Callable[
    [str, Mapping[str, Mapping[ModelOutputName, OutputData]]],
    Mapping[str, Mapping[ElementOutputName, OutputData]],
]


class ElementRegistryEntry(NamedTuple):
    """Registry entry for an element type.

    The create_model_elements and outputs fields are callables that:
        - create_model_elements(config) -> list[dict[str, Any]]
            Transforms config element to model elements
        - outputs(name, outputs) -> dict[str, dict[str, Any]]
            Transforms model outputs to device outputs
    """

    schema: type[Any]
    data: type[Any]
    defaults: dict[str, Any]
    translation_key: ElementType
    create_model_elements: CreateModelElementsFn
    outputs: OutputsFn


ELEMENT_TYPES: dict[ElementType, ElementRegistryEntry] = {
    battery.ELEMENT_TYPE: ElementRegistryEntry(
        schema=battery.BatteryConfigSchema,
        data=battery.BatteryConfigData,
        defaults=battery.CONFIG_DEFAULTS,
        translation_key=battery.ELEMENT_TYPE,
        create_model_elements=battery.create_model_elements,
        outputs=battery.outputs,
    ),
    connection.ELEMENT_TYPE: ElementRegistryEntry(
        schema=connection.ConnectionConfigSchema,
        data=connection.ConnectionConfigData,
        defaults=connection.CONFIG_DEFAULTS,
        translation_key=connection.ELEMENT_TYPE,
        create_model_elements=connection.create_model_elements,
        outputs=connection.outputs,
    ),
    photovoltaics.ELEMENT_TYPE: ElementRegistryEntry(
        schema=photovoltaics.PhotovoltaicsConfigSchema,
        data=photovoltaics.PhotovoltaicsConfigData,
        defaults=photovoltaics.CONFIG_DEFAULTS,
        translation_key=photovoltaics.ELEMENT_TYPE,
        create_model_elements=photovoltaics.create_model_elements,
        outputs=photovoltaics.outputs,
    ),
    grid.ELEMENT_TYPE: ElementRegistryEntry(
        schema=grid.GridConfigSchema,
        data=grid.GridConfigData,
        defaults=grid.CONFIG_DEFAULTS,
        translation_key=grid.ELEMENT_TYPE,
        create_model_elements=grid.create_model_elements,
        outputs=grid.outputs,
    ),
    load.ELEMENT_TYPE: ElementRegistryEntry(
        schema=load.LoadConfigSchema,
        data=load.LoadConfigData,
        defaults=load.CONFIG_DEFAULTS,
        translation_key=load.ELEMENT_TYPE,
        create_model_elements=load.create_model_elements,
        outputs=load.outputs,
    ),
    node.ELEMENT_TYPE: ElementRegistryEntry(
        schema=node.NodeConfigSchema,
        data=node.NodeConfigData,
        defaults=node.CONFIG_DEFAULTS,
        translation_key=node.ELEMENT_TYPE,
        create_model_elements=node.create_model_elements,
        outputs=node.outputs,
    ),
}


class ValidatedElementSubentry(NamedTuple):
    """Validated element subentry with structured configuration."""

    name: str
    element_type: ElementType
    subentry: ConfigSubentry
    config: ElementConfigSchema


def is_element_config_schema(value: Any) -> TypeGuard[ElementConfigSchema]:
    """Return True when value matches any ElementConfigSchema TypedDict."""

    if not isinstance(value, Mapping):
        return False

    element_type = value.get(CONF_ELEMENT_TYPE)
    if element_type not in ELEMENT_TYPES:
        return False

    entry = ELEMENT_TYPES[element_type]
    schema = schema_for_type(entry.schema)

    try:
        schema({k: v for k, v in value.items() if k != CONF_ELEMENT_TYPE})  # validate without the element_type field
    except (vol.Invalid, vol.MultipleInvalid):
        return False

    return True


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
    "ELEMENT_TYPES",
    "ELEMENT_TYPE_BATTERY",
    "ELEMENT_TYPE_CONNECTION",
    "ELEMENT_TYPE_GRID",
    "ELEMENT_TYPE_LOAD",
    "ELEMENT_TYPE_NODE",
    "ELEMENT_TYPE_PHOTOVOLTAICS",
    "CreateModelElementsFn",
    "ElementConfigData",
    "ElementConfigSchema",
    "ElementRegistryEntry",
    "ElementType",
    "OutputsFn",
    "ValidatedElementSubentry",
    "collect_element_subentries",
    "is_element_config_schema",
]

"""Constant load element configuration for HAEO integration."""

from typing import Any, Final, Literal, TypedDict

from custom_components.haeo.schema.fields import NameFieldData, NameFieldSchema, PowerFieldData, PowerFieldSchema

ELEMENT_TYPE: Final = "constant_load"

CONF_POWER: Final = "power"


class ConstantLoadConfigSchema(TypedDict):
    """Constant load element configuration."""

    element_type: Literal["constant_load"]
    name: NameFieldSchema
    power: PowerFieldSchema


class ConstantLoadConfigData(TypedDict):
    """Constant load element configuration."""

    element_type: Literal["constant_load"]
    name: NameFieldData
    power: PowerFieldData


CONSTANT_LOAD_CONFIG_DEFAULTS: dict[str, Any] = {}


def model_description(config: ConstantLoadConfigData) -> str:
    """Generate device model string from constant load configuration."""
    return f"Constant Load {config['power']:.1f}kW"

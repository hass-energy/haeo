"""Tests for the junction element adapter."""

from homeassistant.core import HomeAssistant

from custom_components.haeo.core.adapters.elements.junction import JUNCTION_DEVICE_JUNCTION, JUNCTION_POWER_BALANCE
from custom_components.haeo.core.adapters.elements.junction import adapter as junction_adapter
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import ELEMENT_POWER_BALANCE
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.junction import JunctionConfigData, JunctionConfigSchema
from custom_components.haeo.elements.availability import schema_config_available


async def test_available_returns_true(hass: HomeAssistant) -> None:
    """A junction has no sensor dependencies, so it is always available."""
    config: JunctionConfigSchema = {"element_type": ElementType.JUNCTION, "name": "Switchboard"}

    assert schema_config_available(config, sm=hass.states) is True


def test_model_elements_is_pure_junction() -> None:
    """A junction is a model node that neither produces nor consumes power."""
    config: JunctionConfigData = {"element_type": ElementType.JUNCTION, "name": "Switchboard"}

    assert junction_adapter.model_elements(config) == [
        {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "Switchboard", "is_source": False, "is_sink": False}
    ]


def test_outputs_maps_power_balance() -> None:
    """The model node's power balance becomes the junction's power balance output."""
    balance = OutputData(type=OutputType.SHADOW_PRICE, unit="$/kW", values=(0.1, 0.2))

    outputs = junction_adapter.outputs("Switchboard", {"Switchboard": {ELEMENT_POWER_BALANCE: balance}})

    assert outputs == {JUNCTION_DEVICE_JUNCTION: {JUNCTION_POWER_BALANCE: balance}}


def test_outputs_without_power_balance_is_empty() -> None:
    """A junction whose node has no power balance output has no outputs."""
    assert junction_adapter.outputs("Switchboard", {"Switchboard": {}}) == {JUNCTION_DEVICE_JUNCTION: {}}

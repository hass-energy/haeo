"""Buffer element adapter for model layer integration."""

from collections.abc import Mapping
from typing import Final, Literal

from custom_components.haeo.core.adapters.elements.battery import charge_connection_name, discharge_connection_name
from custom_components.haeo.core.adapters.elements.solar import solar_connection_name
from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BUFFER
from custom_components.haeo.core.model.elements import buffer as model_buffer
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import (
    CONF_GENERATION,
    CONF_KIND,
    CONF_LEVEL,
    CONF_LOADS,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    ELEMENT_TYPE,
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
    BufferConfigData,
)

type BufferOutputName = Literal[
    "buffer_energy_required",
    "buffer_energy_available",
    "buffer_energy_shortfall",
    "buffer_state_of_charge",
]

BUFFER_OUTPUT_NAMES: Final[frozenset[BufferOutputName]] = frozenset(
    (
        BUFFER_ENERGY_REQUIRED := "buffer_energy_required",
        BUFFER_ENERGY_AVAILABLE := "buffer_energy_available",
        BUFFER_ENERGY_SHORTFALL := "buffer_energy_shortfall",
        BUFFER_STATE_OF_CHARGE := "buffer_state_of_charge",
    )
)

type BufferDeviceName = Literal[ElementType.BUFFER]

BUFFER_DEVICE_NAMES: Final[frozenset[BufferDeviceName]] = frozenset((BUFFER_DEVICE_BUFFER := ElementType.BUFFER,))


class BufferAdapter:
    """Adapter for Buffer elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = False

    def model_elements(self, config: BufferConfigData) -> list[ModelElementConfig]:
        """Create the buffer model element over its loads, generation, and batteries.

        Generation counts by the limit on the connection it produces through. A
        reserve flows through each battery's discharge connection and headroom
        through its charge connection.
        """
        participants = config[SECTION_PARTICIPANTS]
        requirement = config[SECTION_REQUIREMENT]
        connection_name = discharge_connection_name if config[CONF_KIND] == KIND_RESERVE else charge_connection_name
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_BUFFER,
                "name": config["name"],
                "kind": config[CONF_KIND],
                "loads": list(participants.get(CONF_LOADS, [])),
                "generation": [
                    {"element": generator, "connection": solar_connection_name(generator)}
                    for generator in participants.get(CONF_GENERATION, [])
                ],
                "storage": [
                    {"battery": battery, "connection": connection_name(battery)}
                    for battery in participants[CONF_STORAGE]
                ],
                "window": requirement[CONF_WINDOW],
                "level": requirement.get(CONF_LEVEL),
                "price": config[SECTION_PRICING][CONF_SHORTFALL_COST],
            }
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: object,
    ) -> Mapping[BufferDeviceName, Mapping[BufferOutputName, OutputData]]:
        """Map model outputs to buffer output names."""
        outputs = model_outputs[name]
        return {
            BUFFER_DEVICE_BUFFER: {
                BUFFER_ENERGY_REQUIRED: expect_output_data(outputs[model_buffer.BUFFER_ENERGY_REQUIRED]),
                BUFFER_ENERGY_AVAILABLE: expect_output_data(outputs[model_buffer.BUFFER_ENERGY_AVAILABLE]),
                BUFFER_ENERGY_SHORTFALL: expect_output_data(outputs[model_buffer.BUFFER_ENERGY_SHORTFALL]),
                BUFFER_STATE_OF_CHARGE: expect_output_data(outputs[model_buffer.BUFFER_STATE_OF_CHARGE]),
            }
        }


adapter = BufferAdapter()

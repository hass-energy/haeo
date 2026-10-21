"""Deferrable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
    SegmentSpec,
)
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_OVERAGE,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
    DeferrableLoadElementConfig,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import CONF_LOADS, BufferRole
from custom_components.haeo.core.schema.elements.deferrable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DUE,
    CONF_ENERGY_METER,
    CONF_IN_WINDOW,
    CONF_MAX_POWER,
    CONF_OPENED,
    CONF_OVERAGE_PRICE,
    CONF_WINDOW_START,
    ELEMENT_TYPE,
    SECTION_POWER,
    SECTION_PRICING,
    SECTION_SCHEDULE,
    DeferrableLoadConfigData,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Deferrable-load-specific output names for translation/sensor mapping
type DeferrableLoadElementOutputName = Literal[
    "deferrable_load_power",
    "deferrable_load_energy_delivered",
    "deferrable_load_energy_shortfall",
    "deferrable_load_energy_overage",
]

DEFERRABLE_LOAD_ELEMENT_OUTPUT_NAMES: Final[frozenset[DeferrableLoadElementOutputName]] = frozenset(
    (
        DEFERRABLE_POWER := "deferrable_load_power",
        DEFERRABLE_ENERGY_DELIVERED := "deferrable_load_energy_delivered",
        DEFERRABLE_ENERGY_SHORTFALL := "deferrable_load_energy_shortfall",
        DEFERRABLE_ENERGY_OVERAGE := "deferrable_load_energy_overage",
    )
)

type DeferrableLoadDeviceName = Literal[ElementType.DEFERRABLE_LOAD]

DEFERRABLE_LOAD_DEVICE_NAMES: Final[frozenset[DeferrableLoadDeviceName]] = frozenset(
    (DEFERRABLE_LOAD_DEVICE := ElementType.DEFERRABLE_LOAD,),
)


class DeferrableLoadAdapter:
    """Adapter for deferrable load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = True
    switchboard: bool = False
    device_names: frozenset[DeferrableLoadDeviceName] = DEFERRABLE_LOAD_DEVICE_NAMES
    buffer_roles: frozenset[BufferRole] = frozenset({CONF_LOADS})

    def model_elements(self, config: DeferrableLoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for deferrable load configuration.

        Creates 2 model elements:
        1. {name} - Deferrable load (energy requirement per calendar window)
        2. {name}:connection - Connection (network → load)

        Calendar events define the run windows; each event's text carries the
        energy it must receive, such as "3 kWh". Overlapping events share one
        window, but each event's energy must arrive between its own start and
        end: a shortfall is priced at the deficit price where the event ends,
        and delivery beyond what has started at the overage price, never
        forbidden.

        The energy meter's rise since the open window began becomes that
        window's initial energy, so each re-optimization only plans the
        remainder of it.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        pricing = config[SECTION_PRICING]
        power = config.get(SECTION_POWER, {})

        load: DeferrableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
            "name": name,
            "is_source": False,
            "is_sink": True,
            "in_window": schedule[CONF_IN_WINDOW],
            "window_start": schedule[CONF_WINDOW_START],
            "opened": schedule[CONF_OPENED],
            "due": schedule[CONF_DUE],
            "initial_energy": schedule.get(CONF_ENERGY_METER, 0.0),
            "deficit_price": pricing[CONF_DEFICIT_PRICE],
            "overage_price": pricing[CONF_OVERAGE_PRICE],
        }

        max_power = power.get(CONF_MAX_POWER)
        segments: dict[str, SegmentSpec] = (
            {} if max_power is None else {"power_limit": {"segment_type": "power_limit", "max_power": max_power}}
        )

        return [
            load,
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": segments,
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: DeferrableLoadConfigData,  # noqa: ARG002 (protocol signature)
        **_kwargs: object,
    ) -> Mapping[DeferrableLoadDeviceName, Mapping[DeferrableLoadElementOutputName, OutputData]]:
        """Map model outputs to deferrable-load-specific output names."""
        load_outputs = model_outputs[name]
        connection = model_outputs.get(f"{name}:connection")

        delivered = expect_output_data(load_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED])
        shortfall = expect_output_data(load_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL])
        overage = expect_output_data(load_outputs[DEFERRABLE_LOAD_ENERGY_OVERAGE])
        period_count = len(delivered.values) - 1

        power = replace(connection_power(connection, period_count), type=OutputType.POWER, direction="-")

        return {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: power,
                DEFERRABLE_ENERGY_DELIVERED: replace(delivered, type=OutputType.ENERGY),
                DEFERRABLE_ENERGY_SHORTFALL: replace(shortfall, type=OutputType.ENERGY),
                DEFERRABLE_ENERGY_OVERAGE: replace(overage, type=OutputType.ENERGY),
            }
        }


adapter = DeferrableLoadAdapter()

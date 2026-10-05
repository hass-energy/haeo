"""Deferrable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.calendar_windows import calendar_windows
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
from custom_components.haeo.core.schema.elements.deferrable_load import (
    CONF_DEFICIT_PRICE,
    CONF_ENERGY_DELIVERED,
    CONF_MAX_POWER,
    CONF_OVERAGE_PRICE,
    CONF_WINDOW_CALENDAR,
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
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED
    can_source: bool = False
    can_sink: bool = True

    def model_elements(self, config: DeferrableLoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for deferrable load configuration.

        Creates 2 model elements:
        1. {name} - Deferrable load (energy requirement per calendar window)
        2. {name}:connection - Connection (network → load)

        Calendar events define the run windows; each event's text carries the
        energy (kWh) that window must receive. Overlapping events merge into
        one window with their energy summed. Each window is settled at its
        end: a shortfall is priced at the deficit price, and delivery beyond
        the requirement is priced at the overage price, or forbidden when no
        overage price is configured.

        Energy the delivered sensor reports becomes the initial energy of the
        window open at the horizon start, so each re-optimization only plans
        the remainder of that window. It never counts toward a later window.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        pricing = config[SECTION_PRICING]
        power = config.get(SECTION_POWER, {})

        windows = calendar_windows(schedule[CONF_WINDOW_CALENDAR])
        n_boundaries = len(windows.requirement)

        # A negative reading is a sensor fault, never energy taken back out.
        initial_energy = max(schedule.get(CONF_ENERGY_DELIVERED, 0.0), 0.0)

        # Penalty prices are clamped at zero: the model rejects negative
        # prices, and an entity can report one even though the form cannot.
        deficit_price = np.maximum(pricing[CONF_DEFICIT_PRICE], 0.0)
        overage_price = pricing.get(CONF_OVERAGE_PRICE)

        load: DeferrableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
            "name": name,
            "in_window": windows.in_window,
            "window_start": windows.window_start,
            "requirement": windows.requirement,
            "initial_energy": initial_energy,
            "deficit_price": _to_boundaries(deficit_price, n_boundaries),
            "overage_price": (
                None if overage_price is None else _to_boundaries(np.maximum(overage_price, 0.0), n_boundaries)
            ),
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
        **_kwargs: Any,
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


def _to_boundaries(
    value: NDArray[np.floating[Any]] | float,
    n_boundaries: int,
) -> NDArray[np.floating[Any]] | float:
    """Extend an interval-shaped series to boundary length by repeating the end."""
    if not isinstance(value, np.ndarray):
        return value
    if len(value) == n_boundaries - 1:
        return np.append(value, value[-1])
    return value

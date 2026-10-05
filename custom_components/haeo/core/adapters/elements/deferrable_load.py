"""Deferrable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_ABSORBED,
    DEFERRABLE_LOAD_ENERGY_DEFICIT,
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

# Effectively unlimited power (kW) for window-gated flow when no physical
# device power limit is configured.
_UNLIMITED_POWER: Final = 1.0e6

# Deferrable-load-specific output names for translation/sensor mapping
type DeferrableLoadElementOutputName = Literal[
    "deferrable_load_power",
    "deferrable_load_energy_absorbed",
    "deferrable_load_energy_deficit",
]

DEFERRABLE_LOAD_ELEMENT_OUTPUT_NAMES: Final[frozenset[DeferrableLoadElementOutputName]] = frozenset(
    (
        DEFERRABLE_POWER := "deferrable_load_power",
        DEFERRABLE_ENERGY_ABSORBED := "deferrable_load_energy_absorbed",
        DEFERRABLE_ENERGY_DEFICIT := "deferrable_load_energy_deficit",
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
        2. {name}:connection - Connection (network → load), open only during windows

        Calendar events define the run windows; each event's text carries the
        energy (kWh) that window must absorb. Capacity opens at each window's
        start, the requirement is due by its end, and any locked-in shortfall
        is priced at the deficit price instead of being a hard constraint.

        Energy the delivered sensor reports for a window already open at the
        horizon start becomes the load's initial energy, so each
        re-optimization only plans the remainder of that window.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        pricing = config[SECTION_PRICING]
        power = config.get(SECTION_POWER, {})

        calendar = schedule[CONF_WINDOW_CALENDAR]
        capacity = np.cumsum(calendar["value_edge_start"])
        required = np.cumsum(calendar["value_edge_end"])

        # Windows open at the horizon start have all opened their capacity by
        # the first boundary, so that capacity bounds what can already have
        # been delivered. Clamping keeps a stale or unreset sensor from
        # crediting energy to later windows or to no window at all.
        delivered = schedule.get(CONF_ENERGY_DELIVERED, 0.0)
        initial_energy = min(max(delivered, 0.0), float(capacity[0]))

        # Power may only flow while a window is open.
        window_mask = np.asarray(calendar["presence"][:-1], dtype=np.float64)
        max_power = power.get(CONF_MAX_POWER)
        if max_power is None:
            max_power = _UNLIMITED_POWER
        gated_power = max_power * window_mask

        # Penalty prices are clamped at zero: a negative price on an unbounded
        # shortfall or overage would make the optimization unbounded, and an
        # entity can report one even though the form cannot.
        deficit_price = np.maximum(pricing[CONF_DEFICIT_PRICE], 0.0)
        # Overage is a single end-of-horizon charge, so a series collapses
        # to its first value.
        overage_price = max(float(np.atleast_1d(pricing.get(CONF_OVERAGE_PRICE, 0.0))[0]), 0.0)

        load: DeferrableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
            "name": name,
            "capacity": capacity,
            "required": required,
            "initial_energy": initial_energy,
            "deficit_price": _to_boundaries(deficit_price, len(capacity)),
            "overage_price": overage_price,
        }

        return [
            load,
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": gated_power,
                    },
                },
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

        absorbed = expect_output_data(load_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED])
        deficit = expect_output_data(load_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT])
        period_count = len(absorbed.values) - 1

        power = replace(connection_power(connection, period_count), type=OutputType.POWER, direction="-")

        return {
            DEFERRABLE_LOAD_DEVICE: {
                DEFERRABLE_POWER: power,
                DEFERRABLE_ENERGY_ABSORBED: replace(absorbed, type=OutputType.ENERGY),
                DEFERRABLE_ENERGY_DEFICIT: replace(deficit, type=OutputType.ENERGY),
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

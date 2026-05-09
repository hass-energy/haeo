"""Load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE, LoadConfigData
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    CONF_THRESHOLD_PRICE,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_THRESHOLD,
)

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
    "load_threshold_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow price
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
        # Configured willingness-to-pay ceiling for sheddable loads
        LOAD_THRESHOLD_PRICE := "load_threshold_price",
    )
)

type LoadDeviceName = Literal[ElementType.LOAD]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := ElementType.LOAD,),
)


def _threshold_price(config: LoadConfigData) -> NDArray[np.floating[Any]] | float | None:
    """Return the configured threshold price, or None when absent / disabled.

    Returns None when curtailment is disabled (the load is fixed and the
    threshold has no effect) or when no threshold value is configured.
    """
    if not config.get(SECTION_CURTAILMENT, {}).get(CONF_CURTAILMENT, False):
        return None
    threshold_section = config.get(SECTION_THRESHOLD) or {}
    return threshold_section.get(CONF_THRESHOLD_PRICE)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED
    can_source: bool = False
    can_sink: bool = True

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        sheddable = config.get(SECTION_CURTAILMENT, {}).get(CONF_CURTAILMENT, False)
        segments: dict[str, Any] = {
            "power_limit": {
                "segment_type": "power_limit",
                "max_power": config[SECTION_FORECAST][CONF_FORECAST],
                "fixed": not sheddable,
            },
        }
        # When curtailment is enabled, add a pricing segment encoding the willingness
        # to pay. ``transfer_cost`` is added to the LP objective (which is minimised);
        # we want a *benefit* when load is served, so the segment price is the
        # negation of the user-facing threshold price. Mirrors the grid export
        # convention (``price = -CONF_PRICE_TARGET_SOURCE``).
        threshold = _threshold_price(config)
        if threshold is not None:
            segments["pricing"] = {
                "segment_type": "pricing",
                "price": _negate(threshold),
            }
        return [
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": False,
                "is_sink": True,
            },
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": config["name"],
                "is_time_sensitive": True,
                "segments": segments,
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: LoadConfigData,
        periods: NDArray[np.floating[Any]],
        **_kwargs: Any,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]
        fixed = not config.get(SECTION_CURTAILMENT, {}).get(CONF_CURTAILMENT, False)

        power = expect_output_data(connection[CONNECTION_POWER])
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(power, type=OutputType.POWER, direction="-", fixed=fixed),
        }

        # Shadow price from power_limit segment (if present)
        if (
            isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping)
            and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
            and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
        ):
            load_outputs[LOAD_FORECAST_LIMIT_PRICE] = shadow

        # Configured threshold-price visible as a $/kWh sensor (sheddable loads only)
        threshold = _threshold_price(config)
        if threshold is not None:
            load_outputs[LOAD_THRESHOLD_PRICE] = OutputData(
                type=OutputType.PRICE,
                unit="$/kWh",
                values=tuple(broadcast_to_sequence(threshold, len(periods))),
            )

        return {LOAD_DEVICE_LOAD: load_outputs}


def _negate(value: NDArray[np.floating[Any]] | float) -> NDArray[np.floating[Any]] | float:
    """Negate a scalar price or each element of an array of prices."""
    if isinstance(value, np.ndarray):
        return -value
    return -float(value)


adapter = LoadAdapter()

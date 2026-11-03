"""Load a grid emissions intensity sensor into a value for each period of a plan."""

from collections.abc import Sequence
from datetime import tzinfo
import re
from typing import Final

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.data.util.forecast_fuser import fuse_to_intervals
from custom_components.haeo.core.data.util.input_values import InputError
from custom_components.haeo.core.state import EntityState, StateMachine

from .extractors import ExtractedData, extract

# Mass of CO2 or its equivalent per kWh, as extraction leaves it, with the mass unit captured
_INTENSITY_UNIT: Final = re.compile(r"^(g|kg|t)\s*(?:CO2(?:-?eq?)?)?/kWh$", re.IGNORECASE)
_KILOGRAMS: Final = {"g": 1e-3, "kg": 1.0, "t": 1e3}


def load_emissions_intensity(sm: StateMachine, entity_id: str, forecast_times: Sequence[float]) -> NDArray[np.float64]:
    """Return a sensor's grid emissions intensity in kg/kWh, averaged over each period between the forecast times.

    The sensor can give a constant reading or a forecast, in grams, kilograms or
    tonnes of CO2 or its equivalent per kWh or MWh.

    Raises:
        InputError: If the sensor is missing, has no reading, or is in another unit.

    """
    state = sm.get(entity_id)
    extracted = None if state is None else _extracted(state, sm.time_zone)
    if extracted is None:
        raise InputError(
            translation_key="emissions_intensity_unavailable", translation_placeholders={"entity_id": entity_id}
        )
    match = _INTENSITY_UNIT.match(str(extracted.unit or ""))
    if match is None:
        raise InputError(
            translation_key="emissions_intensity_unit",
            translation_placeholders={"entity_id": entity_id, "unit": str(extracted.unit)},
        )
    scale = _KILOGRAMS[match.group(1).lower()]
    if isinstance(extracted.data, Sequence):
        return np.asarray(fuse_to_intervals(None, extracted.data, forecast_times)) * scale
    return np.full(len(forecast_times) - 1, float(extracted.data) * scale)


def _extracted(state: EntityState, time_zone: tzinfo) -> ExtractedData | None:
    """Return a state's reading or forecast, or None when it has neither."""
    try:
        return extract(state, time_zone=time_zone)
    except ValueError:
        return None


__all__ = ["load_emissions_intensity"]

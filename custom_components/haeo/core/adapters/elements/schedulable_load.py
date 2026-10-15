"""Schedulable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal

import numpy as np

from custom_components.haeo.core.adapters.calendar_windows import calendar_windows
from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
    SchedulableLoadElementConfig,
)
from custom_components.haeo.core.model.elements.schedulable_load import (
    SCHEDULABLE_LOAD_ENERGY_MISSED,
    SCHEDULABLE_LOAD_START,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.schedulable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DURATION,
    CONF_INTEGER_MODE,
    CONF_POWER,
    CONF_RUNNING,
    CONF_RUNNING_OFF_PERIODS,
    CONF_WINDOW_CALENDAR,
    DEFAULT_INTEGER_MODE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_PRICING,
    SECTION_PROFILE,
    SECTION_SCHEDULE,
    SchedulableLoadConfigData,
    ScheduleData,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Readings at or above this count as running, matching availability inputs.
_RUNNING_THRESHOLD: Final = 0.5

_SECONDS_PER_HOUR: Final = 3600.0

# Schedulable-load-specific output names for translation/sensor mapping
type SchedulableLoadElementOutputName = Literal[
    "schedulable_load_power",
    "schedulable_load_start",
    "schedulable_load_energy_missed",
]

SCHEDULABLE_LOAD_ELEMENT_OUTPUT_NAMES: Final[frozenset[SchedulableLoadElementOutputName]] = frozenset(
    (
        SCHEDULABLE_POWER := "schedulable_load_power",
        SCHEDULABLE_START := "schedulable_load_start",
        SCHEDULABLE_ENERGY_MISSED := "schedulable_load_energy_missed",
    )
)

type SchedulableLoadDeviceName = Literal[ElementType.SCHEDULABLE_LOAD]

SCHEDULABLE_LOAD_DEVICE_NAMES: Final[frozenset[SchedulableLoadDeviceName]] = frozenset(
    (SCHEDULABLE_LOAD_DEVICE := ElementType.SCHEDULABLE_LOAD,),
)


class SchedulableLoadAdapter:
    """Adapter for schedulable load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = True
    can_store: bool = False

    def model_elements(self, config: SchedulableLoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for schedulable load configuration.

        Creates 2 model elements:
        1. {name} - Schedulable load (one run of the profile per calendar window)
        2. {name}:connection - Connection (network → load)

        Calendar events define the windows each run must fit inside, and
        overlapping events merge into one window. The profile is a single
        step at the configured power for the configured duration.

        The running sensor ties the plan to what the load is doing. A run
        starts when an off period of the sensor ends. A load running now
        finishes its run from the horizon start, counting from when that run
        started. The window open at the horizon start needs no further run
        when its run already started inside it, whether that run is still
        going or has finished. Without history for a running load, the run
        is taken to have just started.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        profile = config[SECTION_PROFILE]
        pricing = config[SECTION_PRICING]
        advanced = config.get(SECTION_ADVANCED, {})

        calendar = schedule[CONF_WINDOW_CALENDAR]
        windows = calendar_windows(calendar)

        horizon_start = calendar["horizon_start"]
        run_start = _run_start(schedule, horizon_start)
        open_since = calendar["open_since"]
        window_started = (
            windows.in_window[0] > 0.0 and run_start is not None and open_since is not None and run_start >= open_since
        )
        elapsed = (
            (horizon_start - run_start) / _SECONDS_PER_HOUR if run_start is not None and _is_running(schedule) else None
        )

        load: SchedulableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
            "name": name,
            "profile_power": np.array([max(float(profile[CONF_POWER]), 0.0)]),
            "profile_duration": np.array([max(float(profile[CONF_DURATION]), 0.0)]),
            "in_window": windows.in_window,
            "window_start": windows.window_start,
            # Penalty prices are clamped at zero: the model rejects negative
            # prices, and an entity can report one even though the form cannot.
            "deficit_price": max(float(pricing[CONF_DEFICIT_PRICE]), 0.0),
            "elapsed": elapsed,
            "window_started": bool(window_started),
            "integer_mode": advanced.get(CONF_INTEGER_MODE, DEFAULT_INTEGER_MODE),
            "is_source": False,
            "is_sink": True,
        }

        return [
            load,
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": {},
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: SchedulableLoadConfigData,  # noqa: ARG002 (protocol signature)
        **_kwargs: object,
    ) -> Mapping[SchedulableLoadDeviceName, Mapping[SchedulableLoadElementOutputName, OutputData]]:
        """Map model outputs to schedulable-load-specific output names."""
        load_outputs = model_outputs[name]
        connection = model_outputs.get(f"{name}:connection")

        start = expect_output_data(load_outputs[SCHEDULABLE_LOAD_START])
        missed = expect_output_data(load_outputs[SCHEDULABLE_LOAD_ENERGY_MISSED])
        period_count = len(start.values) - 1

        power = replace(connection_power(connection, period_count), type=OutputType.POWER, direction="-")

        return {
            SCHEDULABLE_LOAD_DEVICE: {
                SCHEDULABLE_POWER: power,
                SCHEDULABLE_START: start,
                SCHEDULABLE_ENERGY_MISSED: missed,
            }
        }


adapter = SchedulableLoadAdapter()


def _is_running(schedule: ScheduleData) -> bool:
    """Return True when the running sensor reports the load running now."""
    return float(schedule.get(CONF_RUNNING, 0.0)) >= _RUNNING_THRESHOLD


def _run_start(schedule: ScheduleData, horizon_start: float) -> float | None:
    """Return when the latest run started, in POSIX seconds.

    A run starts when an off period of the running sensor ends. A running
    load whose history shows no such end, or still shows it off, has just
    started. An idle load without one has no known run.
    """
    periods = schedule.get(CONF_RUNNING_OFF_PERIODS, [])
    ended = [end for _start, end in periods if end is not None]
    if _is_running(schedule) and (not ended or periods[-1][1] is None):
        return horizon_start
    return ended[-1] if ended else None

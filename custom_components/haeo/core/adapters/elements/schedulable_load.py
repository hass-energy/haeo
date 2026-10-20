"""Schedulable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal

import numpy as np

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
from custom_components.haeo.core.schema.elements.buffer import CONF_LOADS, BufferRole
from custom_components.haeo.core.schema.elements.schedulable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DURATION,
    CONF_IN_WINDOW,
    CONF_INTEGER_MODE,
    CONF_POWER,
    CONF_RUNNING,
    CONF_WINDOW_START,
    DEFAULT_INTEGER_MODE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_PRICING,
    SECTION_PROFILE,
    SECTION_SCHEDULE,
    SchedulableLoadConfigData,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

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
    buffer_roles: frozenset[BufferRole] = frozenset({CONF_LOADS})

    def model_elements(self, config: SchedulableLoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for schedulable load configuration.

        Creates 2 model elements:
        1. {name} - Schedulable load (one run of the profile per calendar window)
        2. {name}:connection - Connection (network → load)

        Calendar events define the windows each run must fit inside, and
        overlapping events merge into one window. The profile is a single
        step at the configured power for the configured duration.

        The running sensor ties the plan to what the load is doing. It loads
        as how long ago it first switched on in the open window, which is when
        that window's run started. The run continues to completion, so the
        rest of its profile is committed from the horizon start, and the open
        window takes no further run. Once the run's duration has passed,
        nothing of it remains to commit.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        profile = config[SECTION_PROFILE]
        pricing = config[SECTION_PRICING]
        advanced = config.get(SECTION_ADVANCED, {})

        in_window = schedule[CONF_IN_WINDOW]
        running_for = float(schedule.get(CONF_RUNNING, 0.0))
        started = bool(in_window[0] > 0.0 and running_for > 0.0)

        load: SchedulableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
            "name": name,
            "profile_power": np.array([float(profile[CONF_POWER])]),
            "profile_duration": np.array([float(profile[CONF_DURATION])]),
            "in_window": in_window,
            "window_start": schedule[CONF_WINDOW_START],
            "deficit_price": pricing[CONF_DEFICIT_PRICE],
            "elapsed": running_for if started else None,
            "window_started": started,
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

"""Standalone solver shim for running HAEO optimization outside Home Assistant.

Provides mock state classes and a solve_scenario() function that takes JSON strings
(config, inputs, environment) and returns optimization results as JSON.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

import numpy as np

from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.adapters.policy_compilation import compile_policies
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, collect_model_elements
from custom_components.haeo.core.data.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds
from custom_components.haeo.core.data.loader.config_loader import load_element_configs
from custom_components.haeo.core.model.network import Network
from custom_components.haeo.core.schema.elements.element_type import ElementType


class _MockEntityState:
    """Minimal entity state compatible with HA's State interface."""

    def __init__(self, d: dict[str, Any]) -> None:
        self._d = d

    @property
    def entity_id(self) -> str:
        return self._d.get("entity_id", "")

    @property
    def state(self) -> str:
        return self._d.get("state", "")

    @property
    def attributes(self) -> dict[str, Any]:
        return self._d.get("attributes", {})

    def as_dict(self) -> dict[str, Any]:
        return self._d


class _MockStateManager:
    """Minimal state manager that wraps a dict of entity states."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._states = {k: _MockEntityState(v) for k, v in data.items()}

    def get(self, entity_id: str) -> _MockEntityState | None:
        return self._states.get(entity_id)


def solve_scenario(cfg_json: str, inp_json: str, env_json: str) -> str:
    """Solve a scenario from JSON strings and return results as JSON.

    Args:
        cfg_json: Config JSON (participants, tiers, etc.)
        inp_json: Inputs JSON (list of entity state dicts)
        env_json: Environment JSON (optimization_start_time, etc.)

    Returns:
        JSON string with objective, elements, periods, and states dict.

    """
    cfg = json.loads(cfg_json)
    inp = {e["entity_id"]: e for e in json.loads(inp_json)}
    env = json.loads(env_json)

    frozen = datetime.fromisoformat(env["optimization_start_time"])
    ps = tiers_to_periods_seconds(cfg, start_time=frozen)
    ph = np.asarray(ps, dtype=float) / 3600
    ft = generate_forecast_timestamps(ps, start_time=frozen.timestamp())

    lc = load_element_configs(cfg["participants"], _MockStateManager(inp), ft)
    net = Network(name="browser", periods=ph)
    me = list(collect_model_elements(lc))

    pr = []
    for c in lc.values():
        if c.get("element_type") == ElementType.POLICY:
            pr.extend(extract_policy_rules(c))

    comp = compile_policies(me, pr)
    for e in comp["elements"]:
        net.add(e)

    obj = net.optimize()

    # Extract outputs through the adapter layer (same as coordinator)
    model_outputs = {name: element.outputs() for name, element in net.elements.items()}

    # Convert forecast boundary timestamps to ISO strings for the card
    forecast_times_iso = [datetime.fromtimestamp(t, tz=UTC).isoformat() for t in ft]

    states: dict[str, Any] = {}
    errors: list[str] = []
    for element_name, element_config in lc.items():
        element_type = element_config["element_type"]
        if element_type not in ELEMENT_TYPES:
            continue

        adapter = ELEMENT_TYPES[element_type]
        try:
            adapter_outputs = adapter.outputs(
                name=element_name,
                model_outputs=model_outputs,
                config=element_config,
                periods=net.periods,
            )
        except Exception as exc:
            errors.append(f"{element_name} ({element_type}): {exc}")
            continue

        for device_name, device_outputs in adapter_outputs.items():
            for oname, val in device_outputs.items():
                values = val.values

                entity_id = (
                    f"sensor.{element_name.lower().replace(' ', '_')}_{device_name.lower().replace(' ', '_')}_{oname}"
                )
                attrs: dict[str, Any] = {
                    "element_name": element_name,
                    "element_type": str(element_type),
                    "output_name": oname,
                    "field_type": str(val.type),
                    "source_role": "output",
                    "friendly_name": f"{element_name} {oname.replace('_', ' ')}",
                }

                if val.direction is not None:
                    attrs["direction"] = val.direction

                if val.unit is not None:
                    attrs["unit_of_measurement"] = val.unit

                if val.fixed:
                    attrs["fixed"] = True

                if val.priority is not None:
                    attrs["priority"] = val.priority

                if isinstance(values, (list, tuple)) and len(values) > 1:
                    arr = np.asarray(values, dtype=float)
                    forecast = [
                        {"time": forecast_times_iso[i], "value": float(v)}
                        for i, v in enumerate(arr)
                        if i < len(forecast_times_iso)
                    ]
                    attrs["forecast"] = forecast
                    state_val = str(float(arr[-1])) if val.state_last else str(float(arr[0]))
                else:
                    state_val = str(values[0]) if values else "0"

                states[entity_id] = {
                    "state": state_val,
                    "attributes": attrs,
                    "entity_id": entity_id,
                }

    result: dict[str, Any] = {
        "objective": obj,
        "elements": len(net.elements),
        "periods": len(ph),
        "states": states,
    }
    if errors:
        result["errors"] = errors

    return json.dumps(result)

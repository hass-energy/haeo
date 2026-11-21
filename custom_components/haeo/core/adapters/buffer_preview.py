"""Plan once with a buffer as a form has it, to show what the buffer would do.

The buffer's form previews it by planning with the hub's elements and the
buffer as configured so far, then reading the buffer's line and the charge its
batteries would follow. It is the same model the optimizer solves, so the
preview shows the buffer's real effect rather than an estimate.
"""

from collections.abc import Mapping, Sequence
from typing import TypedDict

import numpy as np

from custom_components.haeo.core.adapters.network_builder import build_network
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import Battery, Buffer
from custom_components.haeo.core.schema import is_schema_value
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema, ElementType
from custom_components.haeo.core.schema.elements.buffer import (
    BUFFER_ROLES,
    CONF_KIND,
    CONF_LEVEL,
    CONF_SHORTFALL_COST,
    CONF_STORAGE,
    CONF_WINDOW,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema
from custom_components.haeo.core.schema.none_value import is_none_value


class BufferPreview(TypedDict):
    """What a buffer would do: its line, the charge its batteries would follow, and which batteries they are."""

    kind: str
    buffer: list[float]
    plan: list[float] | None
    storage: list[str]


def _set(value: object) -> bool:
    return is_schema_value(value) and not is_none_value(value)


def _section(form: Mapping[str, object], key: str) -> Mapping[str, object]:
    section = form.get(key)
    return section if isinstance(section, Mapping) else {}


def buffer_config(name: str, form: Mapping[str, object]) -> ElementConfigSchema | None:
    """Return a buffer's config from its form's values, or None while it has no battery, window, or shortfall cost."""
    participants = _section(form, SECTION_PARTICIPANTS)
    requirement = _section(form, SECTION_REQUIREMENT)
    pricing = _section(form, SECTION_PRICING)
    window, level, cost = requirement.get(CONF_WINDOW), requirement.get(CONF_LEVEL), pricing.get(CONF_SHORTFALL_COST)
    roles = {
        role: [str(name) for name in names]
        for role in BUFFER_ROLES
        if isinstance(names := participants.get(role), list) and names
    }
    if CONF_STORAGE not in roles or not _set(window) or not _set(cost):
        return None
    config = {
        CONF_ELEMENT_TYPE: ElementType.BUFFER,
        CONF_NAME: name,
        CONF_KIND: form.get(CONF_KIND, "reserve"),
        SECTION_PARTICIPANTS: roles,
        SECTION_REQUIREMENT: {CONF_WINDOW: window, **({CONF_LEVEL: level} if _set(level) else {})},
        SECTION_PRICING: {CONF_SHORTFALL_COST: cost},
    }
    return config if is_element_config_schema(config) else None


def storage_state_of_charge(network: Network, names: Sequence[str]) -> list[float] | None:
    """Return the combined state of charge the named batteries follow in a solved network, or None without a plan."""
    batteries = [element for name in names if isinstance(element := network.elements.get(name), Battery)]
    if not batteries or len(batteries) != len(names):
        return None
    try:
        stored = sum(
            np.asarray(battery.outputs()["battery_energy_stored"].values, dtype=float) for battery in batteries
        )
    except (KeyError, RuntimeError, ValueError):
        return None
    capacity = sum(np.asarray(battery.capacity, dtype=float) for battery in batteries)
    ratio = np.divide(stored, capacity, out=np.zeros_like(capacity), where=capacity > 0.0)
    return ratio.tolist()


def preview_buffer(
    participants: Mapping[str, ElementConfigData], periods_seconds: Sequence[float], name: str
) -> BufferPreview:
    """Plan with the hub's elements and the buffer named ``name``, and return what the buffer would do."""
    network = build_network("buffer_preview", participants, periods_seconds)
    network.optimize()
    buffer = network.elements[name]
    if not isinstance(buffer, Buffer):
        msg = f"{name} is not a buffer"
        raise TypeError(msg)
    line = buffer.outputs()["buffer_state_of_charge"]
    storage = buffer.storage_names
    return {
        "kind": str(participants[name].get(CONF_KIND, "reserve")),
        "buffer": list(line.values),
        "plan": storage_state_of_charge(network, storage),
        "storage": storage,
    }


__all__ = ["BufferPreview", "buffer_config", "preview_buffer", "storage_state_of_charge"]

"""Plan once with a buffer as a form has it, to show what the buffer would do.

The buffer's form previews it by planning with the hub's elements and the
buffer as configured so far, then reading the buffer's line and the charge its
batteries would follow. It is the same model the optimizer solves, so the
preview shows the buffer's real effect rather than an estimate.
"""

from collections.abc import Mapping, Sequence
from itertools import count
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
    KIND_RESERVE,
    SECTION_PARTICIPANTS,
    SECTION_PRICING,
    SECTION_REQUIREMENT,
)
from custom_components.haeo.core.schema.elements.conformance import is_element_config_schema
from custom_components.haeo.core.schema.none_value import is_none_value


class BufferPreview(TypedDict):
    """What a buffer would do: its line, and the charge its batteries would follow with it and without it."""

    kind: str
    buffer: list[float]
    plan: list[float] | None
    current: list[float] | None
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
        CONF_KIND: form.get(CONF_KIND, KIND_RESERVE),
        SECTION_PARTICIPANTS: roles,
        SECTION_REQUIREMENT: {CONF_WINDOW: window, **({CONF_LEVEL: level} if _set(level) else {})},
        SECTION_PRICING: {CONF_SHORTFALL_COST: cost},
    }
    return config if is_element_config_schema(config) else None


def storage_state_of_charge(network: Network, names: Sequence[str]) -> list[float] | None:
    """Return the combined state of charge the named batteries follow in a solved network, or None without them all."""
    batteries = [element for name in names if isinstance(element := network.elements.get(name), Battery)]
    if not batteries or len(batteries) != len(names):
        return None
    stored = sum(np.asarray(battery.outputs()["battery_energy_stored"].values, dtype=float) for battery in batteries)
    capacity = sum(np.asarray(battery.capacity, dtype=float) for battery in batteries)
    ratio = np.divide(stored, capacity, out=np.zeros_like(capacity), where=capacity > 0.0)
    return ratio.tolist()


def unused_name(participants: Mapping[str, object], name: str) -> str:
    """Return ``name``, numbered if an element already has it."""
    return next(candidate for n in count(1) if (candidate := name if n == 1 else f"{name} {n}") not in participants)


def preview_buffer(
    hub: Mapping[str, ElementConfigData],
    draft: ElementConfigData,
    periods_seconds: Sequence[float],
    *,
    relax_infeasible: bool = False,
) -> BufferPreview:
    """Plan the hub as it is and with the draft buffer in place of any element of its name, and compare them."""
    name = draft[CONF_NAME]
    with_buffer = build_network(
        "buffer_preview", {**hub, name: draft}, periods_seconds, relax_infeasible=relax_infeasible
    )
    with_buffer.optimize()
    buffer = with_buffer.elements[name]
    if not isinstance(buffer, Buffer):
        msg = f"{name} is not a buffer"
        raise TypeError(msg)
    now = build_network("buffer_preview_now", hub, periods_seconds, relax_infeasible=relax_infeasible)
    now.optimize()
    storage = buffer.storage_names
    return {
        "kind": buffer.kind,
        "buffer": list(buffer.outputs()["buffer_state_of_charge"].values),
        "plan": storage_state_of_charge(with_buffer, storage),
        "current": storage_state_of_charge(now, storage),
        "storage": storage,
    }


__all__ = ["BufferPreview", "buffer_config", "preview_buffer", "storage_state_of_charge", "unused_name"]

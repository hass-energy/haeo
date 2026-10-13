"""Backup energy reserve derived from the network's loads and generation.

The reserve at each forecast boundary is the energy the network would need from
storage to ride through a grid outage that starts at that boundary and lasts
for a window of time. Adding up every element's net demand gives a running
energy balance, and the reserve is the deepest that balance falls below its
starting point within the window: the windowed maximum drawdown.

Elements take part through two protocols on their adapters:

- A ``ReserveContributor`` reports the energy it draws from (or supplies to)
  the reserve in each period.
- A ``ReserveHolder`` turns its share of the reserve into the value of a field
  configured with a reserve schema value.
"""

from collections.abc import Iterator, Mapping, Sequence
from typing import (
    Any,  # noqa: TID251  # adapter Protocols: each adapter narrows config to its own *ConfigData type
    Protocol,
    runtime_checkable,
)

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.schema import is_reserve_value
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementConfigSchema

type ReserveFieldPath = tuple[str, str]
type ReserveFieldKey = tuple[str, ReserveFieldPath]


@runtime_checkable
class ReserveContributor(Protocol):
    """Adapter for an element whose demand or generation counts toward the reserve."""

    def reserve_energy(self, config: Any, periods: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the energy drawn from the reserve in each period in kWh.

        Demand is positive and generation is negative. ``periods`` holds the
        period durations in hours.
        """
        ...


@runtime_checkable
class ReserveHolder(Protocol):
    """Adapter for an element that can hold a share of the reserve."""

    def reserve_capacity(self, config: Any) -> NDArray[np.float64]:
        """Return the energy capacity at each boundary in kWh, used to share the reserve between holders."""
        ...

    def reserve_level(self, config: Any, energy: NDArray[np.float64]) -> NDArray[np.float64]:
        """Return the field value that holds ``energy`` kWh at each boundary."""
        ...


def window_drawdown(
    net_energy: NDArray[np.float64],
    boundaries: Sequence[float] | NDArray[np.float64],
    window: float,
) -> NDArray[np.float64]:
    """Return the energy needed at each boundary to cover net demand over the following window.

    Args:
        net_energy: Net energy demand in each period in kWh (n values).
        boundaries: Boundary timestamps in seconds (n+1 values).
        window: Window length in seconds.

    Returns:
        Reserve energy at each boundary in kWh (n+1 values). Windows that run
        past the end of the horizon only cover the part inside it.

    """
    times = np.asarray(boundaries, dtype=float)
    balance = np.concatenate(([0.0], np.cumsum(net_energy, dtype=float)))
    ends = times + window
    stops = np.searchsorted(times, ends, side="right")

    reserve = np.empty_like(balance)
    for index, (end, stop) in enumerate(zip(ends, stops, strict=True)):
        peak = float(balance[index:stop].max())
        if stop < len(times):
            # Demand is constant within a period, so the balance is linear between boundaries
            peak = max(peak, float(np.interp(end, times, balance)))
        reserve[index] = peak - balance[index]
    return reserve


def reserve_net_energy(
    participants: Mapping[str, ElementConfigData],
    periods: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Return the network's net energy demand in each period in kWh.

    Args:
        participants: Loaded element configurations keyed by element name.
        periods: Period durations in hours.

    """
    net_energy = np.zeros(len(periods), dtype=float)
    for config in participants.values():
        adapter = ELEMENT_TYPES[config[CONF_ELEMENT_TYPE]]
        if isinstance(adapter, ReserveContributor):
            net_energy += adapter.reserve_energy(config, periods)
    return net_energy


def iter_reserve_fields(config: ElementConfigSchema) -> Iterator[tuple[ReserveFieldPath, float]]:
    """Yield the path and window in hours of every field configured with a reserve value."""
    for section_name, section in config.items():
        if not isinstance(section, Mapping):
            continue
        for field_name, value in section.items():
            if is_reserve_value(value):
                yield (section_name, field_name), float(value["value"])


def resolve_reserves(
    participants: Mapping[str, ElementConfigSchema],
    loaded: Mapping[str, ElementConfigData],
    forecast_times: Sequence[float],
) -> dict[ReserveFieldKey, NDArray[np.float64]]:
    """Return the value of every reserve field, keyed by element name and field path.

    Holders share the reserve in proportion to their capacity, so several
    batteries together hold the reserve once rather than each holding all of it.

    Args:
        participants: Element configurations as stored, keyed by element name.
        loaded: Loaded element configurations keyed by element name.
        forecast_times: Boundary timestamps in seconds (n+1 values).

    """
    fields = [
        (name, path, window) for name, config in participants.items() for path, window in iter_reserve_fields(config)
    ]
    if not fields:
        return {}

    holders: dict[str, ReserveHolder] = {}
    for name, _path, _window in fields:
        adapter = ELEMENT_TYPES[loaded[name][CONF_ELEMENT_TYPE]]
        if not isinstance(adapter, ReserveHolder):
            msg = f"Element '{name}' cannot hold a reserve"
            raise TypeError(msg)
        holders[name] = adapter

    times = np.asarray(forecast_times, dtype=float)
    net_energy = reserve_net_energy(loaded, np.diff(times) / 3600)
    capacities = {name: holder.reserve_capacity(loaded[name]) for name, holder in holders.items()}
    total_capacity = np.sum(list(capacities.values()), axis=0)
    shares = {
        name: np.divide(capacity, total_capacity, out=np.zeros_like(capacity), where=total_capacity > 0)
        for name, capacity in capacities.items()
    }

    return {
        (name, path): holders[name].reserve_level(
            loaded[name],
            window_drawdown(net_energy, times, window * 3600) * shares[name],
        )
        for name, path, window in fields
    }


def apply_reserves(
    participants: Mapping[str, ElementConfigSchema],
    loaded: Mapping[str, ElementConfigData],
    forecast_times: Sequence[float],
) -> None:
    """Write the value of every reserve field into the loaded element configurations.

    The loaders copy every configured section into its own dict, so the reserve's section is always present.
    """
    for (name, (section_name, field_name)), value in resolve_reserves(participants, loaded, forecast_times).items():
        loaded[name][section_name][field_name] = value  # type: ignore[literal-required]  # paths come from the stored config, so pyright cannot tie them to one TypedDict key


__all__ = [
    "ReserveContributor",
    "ReserveFieldKey",
    "ReserveFieldPath",
    "ReserveHolder",
    "apply_reserves",
    "iter_reserve_fields",
    "reserve_net_energy",
    "resolve_reserves",
    "window_drawdown",
]

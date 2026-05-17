# ruff: noqa: SLF001, PLC0415
"""Graph walk for reserve power: discover island elements and path efficiencies.

Given a Network and a set of island element names, walks the connection graph
to find:
- All loads reachable from the battery group (island loads)
- All generators reachable (island generation)
- The best (highest) discharge efficiency path from each battery to each load

Uses BFS on the connection graph with efficiency product tracking.
The "island" excludes grid connections — everything that remains when
the grid is disconnected.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from custom_components.haeo.core.model.elements.connection import Connection
    from custom_components.haeo.core.model.network import Network


@dataclass
class IslandTopology:
    """Discovered island topology from the graph walk."""

    battery_names: list[str]
    """Battery element names in the island."""

    load_names: list[str]
    """Load (sink) node names reachable from batteries."""

    gen_names: list[str]
    """Generator (source) node names in the island (e.g., solar)."""

    battery_to_load_efficiency: dict[str, dict[str, float]]
    """Best discharge path efficiency from each battery to each load.

    battery_to_load_efficiency[battery_name][load_name] = product of efficiencies.
    """

    battery_avg_efficiency: dict[str, float] = field(default_factory=dict)
    """Average discharge efficiency for each battery (across all reachable loads)."""


def _get_connection_efficiency(conn: Connection) -> float:
    """Extract the scalar efficiency from a connection's efficiency segment.

    Returns the mean efficiency across periods if it varies, or 1.0 if no
    efficiency segment exists.
    """
    from custom_components.haeo.core.model.elements.segments.efficiency import EfficiencySegment

    for segment in conn.segments.values():
        if isinstance(segment, EfficiencySegment) and segment.efficiency is not None:
            return float(np.mean(segment.efficiency))
    return 1.0


def discover_island(
    network: Network,
    *,
    exclude_elements: set[str] | None = None,
) -> IslandTopology:
    """Walk the network graph to discover the island topology.

    The island consists of all elements EXCEPT those in exclude_elements
    (typically grid connections). BFS from each battery finds reachable
    loads and tracks the product of connection efficiencies.

    Args:
        network: The HAEO network model.
        exclude_elements: Element names to exclude from the island
            (grid nodes, sheddable loads). If None, excludes nodes
            with is_source=True and is_sink=True (bidirectional = grid).

    Returns:
        IslandTopology with discovered batteries, loads, generators,
        and path efficiencies.

    """
    from custom_components.haeo.core.model.element import NetworkElement
    from custom_components.haeo.core.model.elements.battery import Battery
    from custom_components.haeo.core.model.elements.connection import Connection

    exclude = exclude_elements or set()

    # Auto-detect grid nodes: source AND sink (bidirectional nodes)
    if not exclude:
        for name, el in network.elements.items():
            if (
                isinstance(el, NetworkElement)
                and not isinstance(el, Battery)
                and getattr(el, "is_source", False)
                and getattr(el, "is_sink", False)
            ):
                exclude.add(name)

    # Build adjacency list from connections (excluding grid connections)
    # Maps node name to list of (neighbor, connection, efficiency) tuples
    adj: dict[str, list[tuple[str, Connection, float]]] = {}
    for el in network.elements.values():
        if not isinstance(el, Connection):
            continue
        if el.name in exclude:
            continue
        src = el._source
        tgt = el._target
        if src in exclude or tgt in exclude:
            continue

        eff = _get_connection_efficiency(el)

        adj.setdefault(src, []).append((tgt, el, eff))
        # Also add reverse direction for reachability
        # (discharge goes battery -> switchboard -> load)

    # Find batteries and categorize nodes
    batteries: list[str] = []
    loads: set[str] = set()
    generators: set[str] = set()

    for name, el in network.elements.items():
        if name in exclude:
            continue
        if isinstance(el, Battery):
            batteries.append(name)
        elif isinstance(el, NetworkElement):
            if getattr(el, "is_sink", False) and not getattr(el, "is_source", False):
                loads.add(name)
            elif getattr(el, "is_source", False) and not getattr(el, "is_sink", False):
                generators.add(name)

    # BFS from each battery to find reachable loads and best efficiency
    battery_to_load_eff: dict[str, dict[str, float]] = {}
    battery_avg_eff: dict[str, float] = {}

    for batt_name in batteries:
        best_eff: dict[str, float] = {}
        queue: deque[tuple[str, float]] = deque()
        queue.append((batt_name, 1.0))
        visited: dict[str, float] = {batt_name: 1.0}

        while queue:
            node, eff_so_far = queue.popleft()
            for neighbor, _conn, conn_eff in adj.get(node, []):
                path_eff = eff_so_far * conn_eff
                if neighbor not in visited or path_eff > visited[neighbor]:
                    visited[neighbor] = path_eff
                    queue.append((neighbor, path_eff))

                    if neighbor in loads:
                        best_eff[neighbor] = max(best_eff.get(neighbor, 0.0), path_eff)

        battery_to_load_eff[batt_name] = best_eff
        if best_eff:
            battery_avg_eff[batt_name] = sum(best_eff.values()) / len(best_eff)
        else:
            battery_avg_eff[batt_name] = 1.0

    return IslandTopology(
        battery_names=batteries,
        load_names=sorted(loads),
        gen_names=sorted(generators),
        battery_to_load_efficiency=battery_to_load_eff,
        battery_avg_efficiency=battery_avg_eff,
    )


def build_reserve_config_from_network(
    network: Network,
    *,
    exclude_elements: set[str] | None = None,
) -> tuple[IslandTopology, Any]:
    """Build a ReserveConfig from the network topology.

    Combines island discovery with extraction of load/gen forecasts
    and battery variables from the network elements.

    Args:
        network: The HAEO network model (must be initialized).
        exclude_elements: Element names to exclude from the island.

    Returns:
        Tuple of (IslandTopology, ReserveConfig).

    """
    from custom_components.haeo.core.model.element import NetworkElement
    from custom_components.haeo.core.model.elements.battery import Battery
    from custom_components.haeo.core.model.elements.connection import Connection
    from custom_components.haeo.core.model.reserve import ReserveConfig

    island = discover_island(network, exclude_elements=exclude_elements)
    n = len(network.periods)

    # Extract load power for each island load
    # Load power = sum of all incoming connection power (fixed connections)
    island_load_power: dict[str, Any] = {}
    for load_name in island.load_names:
        load_el = network.elements.get(load_name)
        if load_el is None or not isinstance(load_el, NetworkElement):
            continue
        # Find incoming connections to this load
        total_power: Any = np.zeros(n)
        for conn, end in load_el._connections:
            if end == "target" and isinstance(conn, Connection):
                # Power flowing into the load
                for power in conn._power_in.values():
                    total_power = total_power + power
        island_load_power[load_name] = total_power

    # Extract generation power for each island generator
    island_gen_power: dict[str, Any] = {}
    for gen_name in island.gen_names:
        gen_el = network.elements.get(gen_name)
        if gen_el is None or not isinstance(gen_el, NetworkElement):
            continue
        total_power: Any = np.zeros(n)
        for conn, end in gen_el._connections:
            if end == "source" and isinstance(conn, Connection):
                for power in conn._power_in.values():
                    total_power = total_power + power
        island_gen_power[gen_name] = total_power

    # Extract battery variables
    battery_stored: dict[str, Any] = {}
    battery_discharge_limit: dict[str, Any] = {}
    for batt_name in island.battery_names:
        batt = network.elements.get(batt_name)
        if batt is None or not isinstance(batt, Battery):
            continue
        battery_stored[batt_name] = batt.stored_energy

        # Find discharge connection power limit
        for conn, end in batt._connections:
            if end == "source" and isinstance(conn, Connection):
                # This is a discharge connection from battery
                for power in conn._power_in.values():
                    battery_discharge_limit.setdefault(batt_name, power)

    config = ReserveConfig(
        island_load_power=island_load_power,
        island_gen_power=island_gen_power,
        battery_stored_energy=battery_stored,
        battery_efficiency=island.battery_avg_efficiency,
        battery_discharge_limit=battery_discharge_limit,
        periods=network.periods,
    )

    return island, config

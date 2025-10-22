"""Validation helpers for HAEO network topology."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from homeassistant.config_entries import ConfigEntry

from .const import CONF_ELEMENT_TYPE, CONF_NAME
from .elements import ELEMENT_TYPE_CONNECTION, ElementConfigSchema, collect_element_subentries
from .elements.connection import CONF_SOURCE, CONF_TARGET, ConnectionConfigSchema


@dataclass(slots=True, frozen=True)
class NetworkConnectivityResult:
    """Connectivity evaluation for a HAEO network."""

    is_connected: bool
    components: tuple[tuple[str, ...], ...]

    @property
    def num_components(self) -> int:
        """Return count of connected components."""

        return len(self.components)

    @property
    def component_sets(self) -> list[set[str]]:
        """Return components as mutable sets."""

        return [set(component) for component in self.components]


def collect_participant_configs(entry: ConfigEntry) -> dict[str, ElementConfigSchema]:
    """Return a mutable copy of participant configurations for an entry."""

    participants: dict[str, ElementConfigSchema] = {}

    for subentry in collect_element_subentries(entry):
        participants[subentry.name] = cast("ElementConfigSchema", dict(subentry.config))

    return participants


def _build_adjacency(participants: Mapping[str, ElementConfigSchema]) -> dict[str, set[str]]:
    """Return adjacency map for element participants."""

    adjacency: dict[str, set[str]] = {}

    for config in participants.values():
        if config[CONF_ELEMENT_TYPE] == ELEMENT_TYPE_CONNECTION:
            continue
        name = cast("str", config[CONF_NAME])
        adjacency.setdefault(name, set())

    for config in participants.values():
        if config[CONF_ELEMENT_TYPE] != ELEMENT_TYPE_CONNECTION:
            continue

        connection_config = cast("ConnectionConfigSchema", config)
        source = cast("str", connection_config[CONF_SOURCE])
        target = cast("str", connection_config[CONF_TARGET])

        adjacency.setdefault(source, set()).add(target)
        adjacency.setdefault(target, set()).add(source)

    return adjacency


def _normalize_components(components: Sequence[Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    """Return sorted, deterministic component tuples."""

    ordered = [tuple(sorted(component)) for component in components]
    ordered.sort()
    return tuple(ordered)


def validate_network_topology(participants: Mapping[str, ElementConfigSchema]) -> NetworkConnectivityResult:
    """Validate connectivity for the provided participant configurations."""

    if not participants:
        return NetworkConnectivityResult(is_connected=True, components=())

    adjacency = _build_adjacency(participants)
    if not adjacency:
        return NetworkConnectivityResult(is_connected=True, components=())

    components: list[set[str]] = []
    visited: set[str] = set()

    for node in sorted(adjacency):
        if node in visited:
            continue

        stack = [node]
        component: set[str] = set()

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            neighbours = adjacency[current]
            stack.extend(neighbour for neighbour in sorted(neighbours, reverse=True) if neighbour not in visited)

        components.append(component)

    normalized = _normalize_components(components)
    is_connected = len(normalized) <= 1
    return NetworkConnectivityResult(is_connected=is_connected, components=normalized)


def format_component_summary(components: Sequence[Sequence[str]], *, separator: str = "\n") -> str:
    """Create human-readable summary of disconnected components."""

    if not components:
        return ""

    lines: list[str] = []
    for index, component in enumerate(components, start=1):
        names = ", ".join(component)
        lines.append(f"{index}) {names}")
    return separator.join(lines)


__all__ = [
    "NetworkConnectivityResult",
    "collect_participant_configs",
    "format_component_summary",
    "validate_network_topology",
]

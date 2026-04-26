"""Network building and connectivity helpers for the HAEO integration.

Provides ``create_network`` which builds the LP network and returns
pre-resolved ``ElementUpdater`` closures for each HA element.  On each
optimization cycle the coordinator calls these updaters with fresh
``ElementConfigData``; they re-derive model values through the adapter
then write directly to the captured ``TrackedParam`` descriptors without
any runtime path resolution.
"""

from collections.abc import Callable, Mapping, Sequence
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.adapters.policy_compilation import CompiledPolicyRule, compile_policies
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, collect_model_elements
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import ModelElementConfig
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricing
from custom_components.haeo.core.model.reactive import TrackedParam
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.repairs import create_disconnected_network_issue, dismiss_disconnected_network_issue
from custom_components.haeo.validation import format_component_summary, validate_network_topology

_LOGGER = logging.getLogger(__name__)

type ElementUpdater = Callable[[ElementConfigData], None]
"""Closure that applies fresh config values to pre-resolved TrackedParams."""

# Sentinel for missing dict paths during value extraction.
_MISSING: object = object()


def _collect_policy_rules(
    participants: Mapping[str, ElementConfigData],
) -> list[CompiledPolicyRule]:
    """Extract compiled policy rules from the single policy participant."""
    policy_participants = [
        config for config in participants.values() if config.get(CONF_ELEMENT_TYPE) == ElementType.POLICY
    ]
    if not policy_participants:
        return []
    if len(policy_participants) > 1:
        _LOGGER.warning("Expected one policy participant, found %d; merging all policy rules", len(policy_participants))
    return [rule for config in policy_participants for rule in extract_policy_rules(config)]


# ---------------------------------------------------------------------------
# TrackedParam discovery
# ---------------------------------------------------------------------------

# Keys in ModelElementConfig dicts that are identity/topology, not values.
_SKIP_KEYS: frozenset[str] = frozenset({"element_type", "name", "segment_type"})


def _discover_setters(
    element: Any,
    config: Mapping[str, Any],
) -> list[tuple[tuple[str, ...], Callable[[object], None]]]:
    """Walk *config* in parallel with *element* to find TrackedParam targets.

    Returns ``(path, setter)`` pairs where *path* is the key sequence in
    the ``ModelElementConfig`` dict and *setter* writes directly to the
    descriptor on the live element.
    """
    result: list[tuple[tuple[str, ...], Callable[[object], None]]] = []

    def _navigate(obj: Any, key: str) -> Any:
        if isinstance(obj, Mapping):
            return obj.get(key)
        return getattr(obj, key, None)

    def _walk(obj: Any, items: Mapping[str, Any], prefix: tuple[str, ...]) -> None:
        for key, value in items.items():
            if key in _SKIP_KEYS:
                continue
            path = (*prefix, key)
            if isinstance(value, Mapping):
                child = _navigate(obj, key)
                if child is not None:
                    _walk(child, value, path)
            elif not isinstance(obj, Mapping):
                descriptor = getattr(type(obj), key, None)
                if isinstance(descriptor, TrackedParam):
                    target = obj
                    attr = key
                    result.append((path, lambda v, t=target, a=attr: setattr(t, a, v)))

    _walk(element, config, ())
    return result


def _extract_at_path(config: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    """Extract a value from a nested dict, returning ``_MISSING`` on failure."""
    current: Any = config
    for key in path:
        if isinstance(current, Mapping) and key in current:
            current = current[key]
        else:
            return _MISSING
    return current


# ---------------------------------------------------------------------------
# Updater builders
# ---------------------------------------------------------------------------


def _build_element_updater(
    network: Network,
    element_type: ElementType,
    initial_model_configs: list[ModelElementConfig],
) -> ElementUpdater:
    """Build an updater for a non-policy element.

    Discovers TrackedParam paths on the initial model configs and captures
    direct setters.  On each call the adapter re-derives values from fresh
    config, then the captured setters write them without path resolution.
    """
    adapter = ELEMENT_TYPES[element_type]

    # Pre-resolve bindings: (model_element_name, [(dict_path, setter), ...])
    element_bindings: list[tuple[str, list[tuple[tuple[str, ...], Callable[[object], None]]]]] = []
    for model_config in initial_model_configs:
        element_name = model_config["name"]
        element = network.elements[element_name]
        setters = _discover_setters(element, model_config)
        if setters:
            element_bindings.append((element_name, setters))

    def update(config: ElementConfigData) -> None:
        fresh_model_configs = adapter.model_elements(config)
        by_name: dict[str, ModelElementConfig] = {cfg["name"]: cfg for cfg in fresh_model_configs}
        for name, setters in element_bindings:
            fresh = by_name.get(name)
            if fresh is None:
                continue
            for path, setter in setters:
                value = _extract_at_path(fresh, path)
                if value is not _MISSING:
                    setter(value)

    return update


def _build_policy_updater(
    network: Network,
    pricing_rule_map: dict[int, list[str]],
) -> ElementUpdater:
    """Build an updater for a policy element.

    Pre-resolves PolicyPricing element references from the pricing rule map.
    On each call, extracts rules from fresh config and writes prices to the
    captured elements.
    """
    # Pre-resolve PolicyPricing element references
    resolved_map: dict[int, list[PolicyPricing]] = {}
    for rule_idx, names in pricing_rule_map.items():
        elements = [element for name in names if isinstance(element := network.elements[name], PolicyPricing)]
        if elements:
            resolved_map[rule_idx] = elements

    def update(config: ElementConfigData) -> None:
        rules = extract_policy_rules(config)
        n_periods = network.n_periods
        for rule_idx, pricing_elements in resolved_map.items():
            if rule_idx >= len(rules):
                stale_price = broadcast_to_sequence(0.0, n_periods)
                for elem in pricing_elements:
                    elem.price = stale_price
                continue
            rule = rules[rule_idx]
            if not rule.get("enabled", True):
                broadcast_price = broadcast_to_sequence(0.0, n_periods)
            else:
                broadcast_price = broadcast_to_sequence(rule["price"], n_periods)
            for elem in pricing_elements:
                elem.price = broadcast_price

    return update


# ---------------------------------------------------------------------------
# Network creation
# ---------------------------------------------------------------------------


async def create_network(
    entry: ConfigEntry,
    *,
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> tuple[Network, dict[str, ElementUpdater]]:
    """Create a new Network from configuration.

    Returns the network and a dict mapping each HA element name to an
    ``ElementUpdater`` closure that writes fresh config values to the
    pre-resolved TrackedParams on the network elements.
    """
    # Convert seconds to hours for model layer
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    net = Network(name=f"haeo_network_{entry.entry_id}", periods=periods_hours)

    if not participants:
        _LOGGER.info("No participants configured for hub - returning empty network")
        return net, {}

    sorted_model_elements: list[ModelElementConfig] = list(collect_model_elements(participants))

    # Compile policy rules into tagged power flow constraints
    policy_rules = _collect_policy_rules(participants)
    result = compile_policies(sorted_model_elements, policy_rules)

    for model_element_config in result["elements"]:
        element_name = model_element_config.get("name")
        try:
            net.add(model_element_config)
        except Exception as e:
            msg = f"Failed to add model element '{element_name}' (type={model_element_config.get('element_type')})"
            _LOGGER.exception(msg)
            raise ValueError(msg) from e

    # Build element updaters now that all elements are in the network
    updaters: dict[str, ElementUpdater] = {}
    for name, config in participants.items():
        element_type = config[CONF_ELEMENT_TYPE]
        if element_type == ElementType.POLICY:
            continue
        adapter = ELEMENT_TYPES[element_type]
        initial_model_configs = adapter.model_elements(config)
        updaters[name] = _build_element_updater(net, element_type, initial_model_configs)

    # Build the policy updater.  The config flow enforces a single policy
    # element, so the pricing_rule_map covers that one element's rules and
    # the shared updater is called exactly once per update cycle.
    if result["pricing_rule_map"]:
        policy_updater = _build_policy_updater(net, result["pricing_rule_map"])
        for name, config in participants.items():
            if config[CONF_ELEMENT_TYPE] == ElementType.POLICY:
                updaters[name] = policy_updater

    return net, updaters


async def evaluate_network_connectivity(
    hass: HomeAssistant,
    entry: ConfigEntry,
    *,
    participants: Mapping[str, ElementConfigData],
) -> None:
    """Validate the network connectivity for an entry and manage repair issues."""
    result = validate_network_topology(participants)

    if result.is_connected:
        dismiss_disconnected_network_issue(hass, entry.entry_id)
        return

    create_disconnected_network_issue(hass, entry.entry_id, result.components)

    summary = format_component_summary(result.components, separator=" | ")
    _LOGGER.warning(
        "Network %s has %d disconnected component(s): %s",
        entry.entry_id,
        result.num_components,
        summary or "no components",
    )


__all__ = [
    "ElementUpdater",
    "create_network",
    "evaluate_network_connectivity",
]

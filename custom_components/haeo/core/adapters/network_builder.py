"""Build the optimization network from loaded element configs.

``build_network`` adds every configured element's model elements to a new
``Network``, and ``build_element_updaters`` returns an ``ElementUpdater`` for
each configured element of it. An updater takes the element's config again, with new values, re-derives its model
values through the adapter, and writes them to the ``TrackedParam`` descriptors
on the live model elements, so the next solve uses them without a rebuild.
"""

from collections.abc import Callable, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.adapters.policy_compilation import (
    CompilationResult,
    CompiledPolicyRule,
    compile_policies,
)
from custom_components.haeo.core.adapters.registry import ELEMENT_TYPES, collect_model_elements
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import ModelElementConfig
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricing
from custom_components.haeo.core.model.reactive import TrackedParam
from custom_components.haeo.core.model.util import broadcast_to_sequence
from custom_components.haeo.core.schema.elements import ElementConfigData
from custom_components.haeo.core.schema.elements.policy import is_policy_config_data

type ElementUpdater = Callable[[ElementConfigData], None]
"""Applies an element's config, with new values, to its live model elements."""

type _Setter = Callable[[object], None]

# Sentinel for missing dict paths during value extraction
_MISSING: object = object()

# Keys in ModelElementConfig dicts that are identity/topology, not values
_SKIP_KEYS: frozenset[str] = frozenset({"element_type", "name", "segment_type"})

SECONDS_PER_HOUR = 3600


def periods_in_hours(periods_seconds: Sequence[float]) -> NDArray[np.float64]:
    """Return period durations in hours, the model's unit of time, from durations in seconds."""
    return np.asarray(periods_seconds, dtype=float) / SECONDS_PER_HOUR


def _policy_rules(participants: Mapping[str, ElementConfigData]) -> list[CompiledPolicyRule]:
    """Return the rules of the one policy element, or none when there is no policy element.

    Raises:
        ValueError: When more than one policy element is configured, which the config flow prevents.

    """
    policies = [config for config in participants.values() if is_policy_config_data(config)]
    if len(policies) > 1:
        msg = f"Expected at most one policy element, found {len(policies)}"
        raise ValueError(msg)
    return [rule for config in policies for rule in extract_policy_rules(config)]


def _discover_setters(element: object, config: Mapping[str, object]) -> list[tuple[tuple[str, ...], _Setter]]:
    """Walk *config* in parallel with *element* to find TrackedParam targets.

    Returns ``(path, setter)`` pairs where *path* is the key sequence in the
    ``ModelElementConfig`` dict and *setter* writes directly to the descriptor
    on the live element.

    *element* and the nested values discovered while walking *config* are
    genuinely heterogeneous: model elements, their segments, and any other
    nested attribute container can appear here, so ``object`` (narrowed via
    isinstance/getattr below) rather than a fixed protocol is the honest type.
    """
    result: list[tuple[tuple[str, ...], _Setter]] = []

    def _navigate(obj: object, key: str) -> object:
        if isinstance(obj, Mapping):
            return obj.get(key)
        return getattr(obj, key, None)

    def _walk(obj: object, items: Mapping[str, object], prefix: tuple[str, ...]) -> None:
        for key, value in items.items():
            if key in _SKIP_KEYS:
                continue
            path = (*prefix, key)
            if isinstance(value, Mapping):
                child = _navigate(obj, key)
                if child is not None:
                    _walk(child, value, path)
            elif not isinstance(obj, Mapping) and isinstance(getattr(type(obj), key, None), TrackedParam):
                result.append((path, lambda v, t=obj, a=key: setattr(t, a, v)))

    _walk(element, config, ())
    return result


def _extract_at_path(config: Mapping[str, object], path: tuple[str, ...]) -> object:
    """Extract a value from a nested dict, returning ``_MISSING`` when the path is absent."""
    current: object = config
    for key in path:
        if not (isinstance(current, Mapping) and key in current):
            return _MISSING
        current = current[key]
    return current


def _element_updater(network: Network, config: ElementConfigData) -> ElementUpdater:
    """Build the updater of an element that is not a policy.

    Discovers the TrackedParam paths of the element's model elements once, so
    each update re-derives values through the adapter and writes them without
    resolving paths again.
    """
    adapter = ELEMENT_TYPES[config[CONF_ELEMENT_TYPE]]
    bindings = [
        (model_config["name"], setters)
        for model_config in adapter.model_elements(config)
        if model_config["name"] in network.elements
        and (setters := _discover_setters(network.elements[model_config["name"]], model_config))
    ]

    def update(fresh: ElementConfigData) -> None:
        by_name: dict[str, ModelElementConfig] = {cfg["name"]: cfg for cfg in adapter.model_elements(fresh)}
        for name, setters in bindings:
            if (model_config := by_name.get(name)) is None:
                continue
            for path, setter in setters:
                if (value := _extract_at_path(model_config, path)) is not _MISSING:
                    setter(value)

    return update


def _policy_updater(network: Network, pricing_rule_map: Mapping[int, list[str]]) -> ElementUpdater:
    """Build the updater of the policy element, which prices each rule's PolicyPricing elements."""
    pricing: dict[int, list[PolicyPricing]] = {
        rule_index: elements
        for rule_index, names in pricing_rule_map.items()
        if (elements := [element for name in names if isinstance(element := network.elements[name], PolicyPricing)])
    }

    def update(config: ElementConfigData) -> None:
        if not is_policy_config_data(config):
            msg = f"Policy updater for {config['name']} received a {config['element_type']} config"
            raise TypeError(msg)
        rules = extract_policy_rules(config)
        for rule_index, elements in pricing.items():
            # A rule that was removed or disabled no longer prices its flows
            active = rule_index < len(rules) and rules[rule_index].get("enabled", True)
            price = broadcast_to_sequence(rules[rule_index]["price"] if active else 0.0, network.n_periods)
            for element in elements:
                element.price = price

    return update


def build_network(
    name: str,
    participants: Mapping[str, ElementConfigData],
    periods_seconds: Sequence[float],
    *,
    relax_infeasible: bool = False,
) -> Network:
    """Build a network from loaded element configs.

    Raises:
        ValueError: When a model element cannot be added, or more than one policy element is configured.

    """
    network = Network(name=name, periods=periods_in_hours(periods_seconds), relax_infeasible=relax_infeasible)
    for model_config in _compile(participants)["elements"]:
        try:
            network.add(model_config)
        except Exception as error:
            msg = f"Failed to add model element '{model_config['name']}' (type={model_config['element_type']})"
            raise ValueError(msg) from error
    return network


def build_element_updaters(
    network: Network, participants: Mapping[str, ElementConfigData]
) -> dict[str, ElementUpdater]:
    """Return an updater for each element of a network that ``build_network`` built from the same configs."""
    policy_updater = _policy_updater(network, _compile(participants)["pricing_rule_map"])
    return {
        element_name: policy_updater if is_policy_config_data(config) else _element_updater(network, config)
        for element_name, config in participants.items()
    }


def _compile(participants: Mapping[str, ElementConfigData]) -> CompilationResult:
    """Return the participants' model elements with their policy rules compiled in."""
    return compile_policies(collect_model_elements(participants), _policy_rules(participants))


__all__ = ["ElementUpdater", "build_element_updaters", "build_network", "periods_in_hours"]

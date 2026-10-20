"""Tests that the element registry and the network element config union agree."""

from typing import Literal, TypeAliasType, get_args, get_type_hints

from custom_components.haeo.core.model.element import NetworkElement
from custom_components.haeo.core.model.elements import (
    ELEMENTS,
    ModelElementConfig,
    NetworkElementConfig,
    SourceElementConfig,
)


def _element_type(config: type) -> str:
    """Return the element type a config TypedDict declares."""
    annotation = get_type_hints(config)["element_type"]
    literal = annotation.__value__ if isinstance(annotation, TypeAliasType) else annotation
    (element_type,) = get_args(literal)
    return element_type


def test_network_element_configs_match_the_registry() -> None:
    """The config union for network elements names exactly the registered NetworkElement subclasses."""
    configs_by_type = {_element_type(config): config for config in get_args(ModelElementConfig)}
    network_types = {
        element_type for element_type, spec in ELEMENTS.items() if issubclass(spec.factory, NetworkElement)
    }

    assert {_element_type(config) for config in get_args(NetworkElementConfig.__value__)} == network_types
    assert network_types <= set(configs_by_type)


def test_source_element_configs_are_the_network_elements_that_may_produce() -> None:
    """The source config union names exactly the network element configs not declared unable to produce."""
    may_produce = {
        _element_type(config)
        for config in get_args(NetworkElementConfig.__value__)
        if get_type_hints(config).get("is_source") != Literal[False]
    }

    assert {_element_type(config) for config in get_args(SourceElementConfig.__value__)} == may_produce

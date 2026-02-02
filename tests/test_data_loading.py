"""Tests for network building."""

from typing import cast

from homeassistant.core import HomeAssistant
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.coordinator import create_network
from custom_components.haeo.elements import ElementConfigData
from custom_components.haeo.elements.connection import CONF_SOURCE, CONF_TARGET, SECTION_ENDPOINTS
from custom_components.haeo.elements.load import CONF_CONNECTION
from custom_components.haeo.elements.node import CONF_IS_SINK, CONF_IS_SOURCE
from custom_components.haeo.sections import (
    SECTION_COMMON,
    SECTION_EFFICIENCY,
    SECTION_FORECAST,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_ROLE,
)


async def test_create_network_successful_loads_load_participant(hass: HomeAssistant) -> None:
    """create_network should populate the network when all fields are available."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="loaded_entry")
    entry.add_to_hass(hass)

    # Provide already-loaded config data (not schemas needing sensor loading)
    loaded_configs = cast(
        "dict[str, ElementConfigData]",
        {
            "main_bus": {
                CONF_ELEMENT_TYPE: "node",
                SECTION_COMMON: {CONF_NAME: "main_bus"},
                SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
            },
            "Baseload": {
                CONF_ELEMENT_TYPE: "load",
                SECTION_COMMON: {CONF_NAME: "Baseload", CONF_CONNECTION: "main_bus"},
                SECTION_FORECAST: {
                    "forecast": [2.5, 2.5, 2.5, 2.5],  # Pre-loaded values in kW
                },
            },
        },
    )

    result = await create_network(
        entry,
        periods_seconds=[1800] * 4,
        participants=loaded_configs,
    )

    np.testing.assert_array_equal(result.periods, [0.5] * 4)  # 1800 seconds = 0.5 hours
    assert "Baseload" in result.elements


async def test_create_network_without_participants_returns_empty_network(hass: HomeAssistant) -> None:
    """create_network should return an empty network when no participants are provided."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="no_participants")
    entry.add_to_hass(hass)

    network = await create_network(
        entry,
        periods_seconds=[1800],
        participants={},
    )

    # Empty network should be returned, not raise an error
    assert network.name == f"haeo_network_{entry.entry_id}"
    assert len(network.elements) == 0


async def test_create_network_sorts_connections_after_elements(hass: HomeAssistant) -> None:
    """Connections should be added after their source/target elements."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="sorted_connections")
    entry.add_to_hass(hass)

    participants = cast(
        "dict[str, ElementConfigData]",
        {
            "line": {
                CONF_ELEMENT_TYPE: "connection",
                SECTION_COMMON: {
                    CONF_NAME: "line",
                },
                SECTION_ENDPOINTS: {
                    CONF_SOURCE: "node_a",
                    CONF_TARGET: "node_b",
                },
                SECTION_POWER_LIMITS: {},
                SECTION_PRICING: {},
                SECTION_EFFICIENCY: {},
            },
            "node_a": {
                CONF_ELEMENT_TYPE: "node",
                SECTION_COMMON: {CONF_NAME: "node_a"},
                SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
            },
            "node_b": {
                CONF_ELEMENT_TYPE: "node",
                SECTION_COMMON: {CONF_NAME: "node_b"},
                SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
            },
        },
    )

    network = await create_network(
        entry,
        periods_seconds=[900],
        participants=participants,
    )

    # Nodes should be added before the connection even though the connection was listed first
    assert list(network.elements.keys()) == ["node_a", "node_b", "line"]


async def test_create_network_add_failure_is_wrapped(hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failures when adding model elements should be wrapped with ValueError."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="add_failure")
    entry.add_to_hass(hass)

    participants = cast(
        "dict[str, ElementConfigData]",
        {
            "node": {
                CONF_ELEMENT_TYPE: "node",
                SECTION_COMMON: {CONF_NAME: "node"},
                SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
            },
        },
    )

    # Force Network.add to raise
    def _raise(*_: object, **__: object) -> None:
        err = RuntimeError("boom")
        raise err

    monkeypatch.setattr("custom_components.haeo.model.Network.add", _raise)

    with pytest.raises(ValueError, match="Failed to add model element 'node'"):
        await create_network(
            entry,
            periods_seconds=[900],
            participants=participants,
        )

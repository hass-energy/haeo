"""Tests for network building."""

from homeassistant.core import HomeAssistant
import numpy as np
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.coordinator import create_network
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, NodeConfigData
from custom_components.haeo.core.schema.elements.policy import PolicyConfigData, PolicyRuleData


async def test_create_network_successful_loads_load_participant(hass: HomeAssistant) -> None:
    """create_network should populate the network when all fields are available."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="loaded_entry")
    entry.add_to_hass(hass)

    main_bus: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "main_bus",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    baseload: LoadConfigData = {
        "element_type": ElementType.LOAD,
        "name": "Baseload",
        "connection": as_connection_target("main_bus"),
        "forecast": {"forecast": np.asarray([2.5, 2.5, 2.5, 2.5], dtype=float)},
        "pricing": {},
        "curtailment": {},
    }
    loaded_configs: dict[str, ElementConfigData] = {
        "main_bus": main_bus,
        "Baseload": baseload,
    }

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


async def test_create_network_applies_policy_rules_to_connections(hass: HomeAssistant) -> None:
    """Policy participants are compiled into tag_costs on connection model elements."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="policy_network")
    entry.add_to_hass(hass)

    line_cfg: ConnectionConfigData = {
        "element_type": ElementType.CONNECTION,
        "name": "line",
        "endpoints": {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        "power_limits": {},
        "pricing": {},
        "efficiency": {},
    }
    node_a: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "node_a",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    node_b: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "node_b",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    policy_rule: PolicyRuleData = {
        "name": "A to B",
        "source": ["node_a"],
        "target": ["node_b"],
        "price": 0.07,
    }
    policies_cfg: PolicyConfigData = {
        "element_type": ElementType.POLICY,
        "name": "Policies",
        "rules": [policy_rule],
    }
    participants: dict[str, ElementConfigData] = {
        "line": line_cfg,
        "node_a": node_a,
        "node_b": node_b,
        "policies": policies_cfg,
    }

    network = await create_network(
        entry,
        periods_seconds=[900],
        participants=participants,
    )

    line = network.elements["line"]
    assert isinstance(line, Connection)
    assert line._tag_costs
    assert line._tag_costs[0]["price"] == pytest.approx(0.07)
    tags = line.connection_tags()
    assert 0 in tags
    assert max(tags) >= 1


async def test_create_network_sorts_connections_after_elements(hass: HomeAssistant) -> None:
    """Connections should be added after their source/target elements."""

    entry = MockConfigEntry(domain=DOMAIN, entry_id="sorted_connections")
    entry.add_to_hass(hass)

    line_cfg: ConnectionConfigData = {
        "element_type": ElementType.CONNECTION,
        "name": "line",
        "endpoints": {
            "source": as_connection_target("node_a"),
            "target": as_connection_target("node_b"),
        },
        "power_limits": {},
        "pricing": {},
        "efficiency": {},
    }
    node_a: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "node_a",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    node_b: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "node_b",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    participants: dict[str, ElementConfigData] = {
        "line": line_cfg,
        "node_a": node_a,
        "node_b": node_b,
    }

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

    node_only: NodeConfigData = {
        "element_type": ElementType.NODE,
        "name": "node",
        "role": {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
    }
    participants: dict[str, ElementConfigData] = {"node": node_only}

    # Force Network.add to raise
    def _raise(*_: object, **__: object) -> None:
        err = RuntimeError("boom")
        raise err

    monkeypatch.setattr("custom_components.haeo.core.model.Network.add", _raise)

    with pytest.raises(ValueError, match="Failed to add model element 'node'"):
        await create_network(
            entry,
            periods_seconds=[900],
            participants=participants,
        )

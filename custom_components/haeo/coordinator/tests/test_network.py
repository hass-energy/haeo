"""Tests for coordinator network utilities."""

from typing import Any

import numpy as np
import pytest

from custom_components.haeo.coordinator.network import (
    _MISSING,
    _build_element_updater,
    _build_policy_updater,
    _collect_policy_rules,
    _discover_setters,
    _extract_at_path,
)
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.core.model.elements import ModelElementConfig
from custom_components.haeo.core.model.elements.connection import Connection, ConnectionElementConfig
from custom_components.haeo.core.model.elements.policy_pricing import ELEMENT_TYPE as MODEL_ELEMENT_TYPE_POLICY_PRICING
from custom_components.haeo.core.model.elements.policy_pricing import (
    PolicyPricing,
    PolicyPricingElementConfig,
    PolicyPricingTerm,
)
from custom_components.haeo.core.model.elements.segments import EfficiencySegment, PowerLimitSegment
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.connection import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_PRICE_SOURCE_TARGET,
    ConnectionConfigData,
)
from custom_components.haeo.core.schema.sections.efficiency import EfficiencyData
from custom_components.haeo.core.schema.sections.power_limits import PowerLimitsData
from custom_components.haeo.core.schema.sections.pricing import PricingData

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_network() -> Network:
    """Create a network with a source, sink, and connection."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "target",
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        }
    )
    return network


def _connection_config(
    *,
    max_power: Any = None,
    price: Any = None,
    efficiency: Any = None,
) -> ConnectionConfigData:
    """Build a connection ConnectionConfigData."""
    power_limits = PowerLimitsData()
    if max_power is not None:
        power_limits[CONF_MAX_POWER_SOURCE_TARGET] = max_power
    pricing = PricingData()
    if price is not None:
        pricing[CONF_PRICE_SOURCE_TARGET] = price
    eff = EfficiencyData()
    if efficiency is not None:
        eff[CONF_EFFICIENCY_SOURCE_TARGET] = efficiency
    return ConnectionConfigData(
        element_type=ElementType.CONNECTION,
        name="conn",
        endpoints={
            "source": as_connection_target("source"),
            "target": as_connection_target("target"),
        },
        power_limits=power_limits,
        pricing=pricing,
        efficiency=eff,
    )


# ---------------------------------------------------------------------------
# _extract_at_path
# ---------------------------------------------------------------------------


def test_extract_at_path_returns_leaf_value() -> None:
    """Nested path extraction returns the leaf value."""
    config = {"a": {"b": {"c": 42}}}
    assert _extract_at_path(config, ("a", "b", "c")) == 42


def test_extract_at_path_returns_missing_for_absent_key() -> None:
    """Missing intermediate key returns the _MISSING sentinel."""
    config: dict[str, Any] = {"a": {"b": 1}}
    assert _extract_at_path(config, ("a", "x", "y")) is _MISSING


# ---------------------------------------------------------------------------
# _discover_setters
# ---------------------------------------------------------------------------


def test_discover_setters_finds_tracked_params() -> None:
    """Setters are created for TrackedParam descriptors on model elements."""
    network = _simple_network()
    conn = network.elements["conn"]
    model_config = {
        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
        "name": "conn",
        "source": "source",
        "target": "target",
        "segments": {
            "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
        },
    }
    setters = _discover_setters(conn, model_config)
    paths = [path for path, _setter in setters]
    assert ("segments", "power_limit", "max_power") in paths


def test_discover_setters_skips_non_tracked_params() -> None:
    """Non-TrackedParam attributes like source/target are not bound."""
    network = _simple_network()
    conn = network.elements["conn"]
    model_config = {
        "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
        "name": "conn",
        "source": "source",
        "target": "target",
        "segments": {
            "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
        },
    }
    setters = _discover_setters(conn, model_config)
    paths = {path for path, _setter in setters}
    assert ("source",) not in paths
    assert ("target",) not in paths


# ---------------------------------------------------------------------------
# _build_element_updater
# ---------------------------------------------------------------------------


def test_element_updater_updates_tracked_params() -> None:
    """Element updater writes fresh values to TrackedParams."""
    network = _simple_network()
    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    pl = conn.segments["power_limit"]
    assert isinstance(pl, PowerLimitSegment)
    assert pl.max_power is not None
    assert pl.max_power[0] == 10.0

    initial_model_configs: list[ModelElementConfig] = [
        ConnectionElementConfig(
            element_type=MODEL_ELEMENT_TYPE_CONNECTION,
            name="conn",
            source="source",
            target="target",
            segments={
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
            },
        )
    ]
    updater = _build_element_updater(network, ElementType.CONNECTION, initial_model_configs)

    fresh_config = _connection_config(max_power=np.array([20.0, 20.0]))
    updater(fresh_config)

    assert pl.max_power[0] == 20.0


def test_element_updater_handles_none_efficiency() -> None:
    """Clearing optional efficiency via updater sets TrackedParam to None."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "target",
            "segments": {
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.95, 0.95])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.10])},
            },
        }
    )

    initial_model_configs: list[ModelElementConfig] = [
        ConnectionElementConfig(
            element_type=MODEL_ELEMENT_TYPE_CONNECTION,
            name="conn",
            source="source",
            target="target",
            segments={
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.95, 0.95])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0, 10.0])},
                "pricing": {"segment_type": "pricing", "price": np.array([0.10, 0.10])},
            },
        )
    ]
    updater = _build_element_updater(network, ElementType.CONNECTION, initial_model_configs)

    fresh_config = _connection_config(
        max_power=np.array([10.0, 10.0]),
        price=np.array([0.10, 0.10]),
    )
    updater(fresh_config)

    conn = network.elements["conn"]
    assert isinstance(conn, Connection)
    efficiency = conn.segments["efficiency"]
    assert isinstance(efficiency, EfficiencySegment)
    assert efficiency.efficiency is None

    network.optimize()


# ---------------------------------------------------------------------------
# _build_policy_updater
# ---------------------------------------------------------------------------


def _policy_network() -> Network:
    """Create a network with a tagged connection and PolicyPricing element."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "src", "is_source": True, "is_sink": False})
    network.add({"element_type": MODEL_ELEMENT_TYPE_NODE, "name": "dst", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": "line",
            "source": "src",
            "target": "dst",
            "tags": {0, 1},
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": np.array([10.0]),
                    "max_power_source_target": np.array([10.0]),
                    "max_power_target_source": np.array([10.0]),
                },
            },
        }
    )
    network.add(
        PolicyPricingElementConfig(
            element_type=MODEL_ELEMENT_TYPE_POLICY_PRICING,
            name="policy_pricing_r0_v1",
            price=0.05,
            terms=[PolicyPricingTerm(connection="line", tag=1)],
        )
    )
    return network


def test_policy_updater_updates_price() -> None:
    """Policy updater writes fresh price to PolicyPricing elements."""
    network = _policy_network()
    updater = _build_policy_updater(network, {0: ["policy_pricing_r0_v1"]})

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        CONF_NAME: "Policies",
        "rules": [{"name": "rule", "enabled": True, "source": ["src"], "target": ["dst"], "price": 0.10}],
    }
    updater(config)

    elem = network.elements["policy_pricing_r0_v1"]
    assert isinstance(elem, PolicyPricing)
    assert elem.price == pytest.approx([0.10])


def test_policy_updater_zeros_disabled_rule() -> None:
    """Policy updater writes zero price for disabled rules."""
    network = _policy_network()
    updater = _build_policy_updater(network, {0: ["policy_pricing_r0_v1"]})

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        CONF_NAME: "Policies",
        "rules": [{"name": "rule", "enabled": False, "source": ["src"], "target": ["dst"], "price": 0.10}],
    }
    updater(config)

    elem = network.elements["policy_pricing_r0_v1"]
    assert isinstance(elem, PolicyPricing)
    assert elem.price == pytest.approx([0.0])


def test_policy_updater_zeros_stale_rules() -> None:
    """Policy updater zeros pricing when rule index exceeds rule count."""
    network = _policy_network()
    updater = _build_policy_updater(network, {0: ["policy_pricing_r0_v1"]})

    config: ElementConfigData = {
        CONF_ELEMENT_TYPE: ElementType.POLICY,
        CONF_NAME: "Policies",
        "rules": [],
    }
    updater(config)

    elem = network.elements["policy_pricing_r0_v1"]
    assert isinstance(elem, PolicyPricing)
    assert elem.price == pytest.approx([0.0])


def test_policy_updater_reenables_rule() -> None:
    """Policy updater restores price when re-enabling a rule."""
    network = _policy_network()
    updater = _build_policy_updater(network, {0: ["policy_pricing_r0_v1"]})

    # Disable
    updater(
        {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            "rules": [{"name": "rule", "enabled": False, "source": ["src"], "target": ["dst"], "price": 0.07}],
        }
    )
    elem = network.elements["policy_pricing_r0_v1"]
    assert isinstance(elem, PolicyPricing)
    assert elem.price == pytest.approx([0.0])

    # Re-enable
    updater(
        {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            "rules": [{"name": "rule", "enabled": True, "source": ["src"], "target": ["dst"], "price": 0.07}],
        }
    )
    assert elem.price == pytest.approx([0.07])


# ---------------------------------------------------------------------------
# _collect_policy_rules
# ---------------------------------------------------------------------------


def test_collect_policy_rules_merges_multiple_policy_participants() -> None:
    """Multiple policy participants are merged into one compiled rules list."""
    participants: dict[str, Any] = {
        "Policies A": {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            "rules": [
                {"name": "A", "enabled": True, "source": ["Solar"], "price": {"type": "constant", "value": 0.01}}
            ],
        },
        "Policies B": {
            CONF_ELEMENT_TYPE: ElementType.POLICY,
            CONF_NAME: "Policies",
            "rules": [{"name": "B", "enabled": True, "target": ["Load"], "price": {"type": "constant", "value": 0.02}}],
        },
    }

    rules = _collect_policy_rules(participants)
    assert len(rules) == 2

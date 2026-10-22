"""Tests for building the optimization network and updating it with edited element configs."""

from collections.abc import Callable

import numpy as np
import pytest

from custom_components.haeo.core.adapters.network_builder import build_element_updaters, build_network, periods_in_hours
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.elements.battery import Battery
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricing
from custom_components.haeo.core.model.elements.segments import EfficiencySegment, PowerLimitSegment
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import ElementConfigData, ElementType
from custom_components.haeo.core.schema.elements.battery import BatteryConfigData
from custom_components.haeo.core.schema.elements.connection import ConnectionConfigData
from custom_components.haeo.core.schema.elements.load import LoadConfigData
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, NodeConfigData
from custom_components.haeo.core.schema.elements.policy import PolicyConfigData, PolicyRuleData

SOURCE = "Source"
SINK = "Sink"
LINE = "Line"
BATTERY = "Battery"
POLICIES = "Policies"


def _node(name: str, *, is_source: bool, is_sink: bool) -> NodeConfigData:
    """Return a node config."""
    return {"element_type": ElementType.NODE, "name": name, "role": {CONF_IS_SOURCE: is_source, CONF_IS_SINK: is_sink}}


def _line(
    *, max_power: float = 5.0, price: float | None = None, efficiency: float | None = None
) -> ConnectionConfigData:
    """Return a connection carrying power from the source to the sink."""
    config: ConnectionConfigData = {
        "element_type": ElementType.CONNECTION,
        "name": LINE,
        "endpoints": {"source": as_connection_target(SOURCE), "target": as_connection_target(SINK)},
        "power_limits": {"max_power_source_target": max_power},
        "pricing": {} if price is None else {"price_source_target": price},
        "efficiency": {} if efficiency is None else {"efficiency_source_target": efficiency},
    }
    return config


def _policies(price: float, *, enabled: bool = True, rules: int = 1) -> PolicyConfigData:
    """Return a policy element pricing flows from the source to the sink."""
    rule: PolicyRuleData = {
        "name": "Source to sink",
        "enabled": enabled,
        "source": [SOURCE],
        "target": [SINK],
        "price": price,
    }
    return {"element_type": ElementType.POLICY, "name": POLICIES, "rules": [rule][:rules]}


def _battery(
    *,
    min_charge: float = 0.2,
    max_charge: float = 0.9,
    charge_limit_cost: float = 100.0,
    discharge_efficiency: float = 1.0,
    salvage_value: float = 0.0,
) -> BatteryConfigData:
    """Return a battery on the sink bus."""
    return BatteryConfigData(
        element_type=ElementType.BATTERY,
        name=BATTERY,
        connection=as_connection_target(SINK),
        storage={"capacity": np.array([10.0, 10.0]), "initial_charge_percentage": 0.5},
        limits={
            "min_charge_percentage": np.array([min_charge, min_charge]),
            "max_charge_percentage": np.array([max_charge, max_charge]),
        },
        power_limits={"max_power_source_target": np.array([1.0]), "max_power_target_source": np.array([0.0])},
        pricing={"salvage_value": salvage_value},
        efficiency={
            "efficiency_source_target": np.array([discharge_efficiency]),
            "efficiency_target_source": np.array([1.0]),
        },
        advanced={"charge_limit_cost": np.array([charge_limit_cost])},
    )


def _line_network(line: ConnectionConfigData | None = None) -> dict[str, ElementConfigData]:
    """Return a source feeding a sink over the line, which pays for the power it carries."""
    return {
        SOURCE: _node(SOURCE, is_source=True, is_sink=False),
        SINK: _node(SINK, is_source=False, is_sink=True),
        LINE: line or _line(),
    }


def _battery_network(**battery: float) -> dict[str, ElementConfigData]:
    """Return a battery on a bus that can take any power it discharges."""
    return {SINK: _node(SINK, is_source=False, is_sink=True), BATTERY: _battery(**battery)}


def _line_segment[T](network: Network, segment_type: type[T], name: str) -> T:
    """Return a segment of the line's model connection."""
    line = network.elements[LINE]
    assert isinstance(line, Connection)
    segment = line.segments[name]
    assert isinstance(segment, segment_type)
    return segment


def _line_max_power(network: Network) -> list[float]:
    """Return the line's power limit in each period."""
    max_power = _line_segment(network, PowerLimitSegment, "power_limit").max_power
    assert max_power is not None
    return np.ravel(max_power).tolist()


def _model_battery(network: Network) -> Battery:
    """Return the battery's model element."""
    battery = network.elements[BATTERY]
    assert isinstance(battery, Battery)
    return battery


def _discharge_drawn(network: Network) -> float:
    """Solve and return the power the battery draws to discharge in the first period."""
    network.optimize()
    discharge = network.elements[f"{BATTERY}:discharge"]
    assert isinstance(discharge, Connection)
    return discharge.extract_values(discharge.total_power_in)[0]


def _policy_price(network: Network) -> float:
    """Return the price the policy element puts on the flows of its rule."""
    pricing = [element for element in network.elements.values() if isinstance(element, PolicyPricing)]
    assert len(pricing) == 1
    return float(np.asarray(pricing[0].price).ravel()[0])


@pytest.mark.parametrize(
    ("participants", "edited", "edit", "observe", "before", "after"),
    [
        pytest.param(
            _line_network(),
            LINE,
            _line(max_power=8.0),
            _line_max_power,
            [5.0],
            [8.0],
            id="connection_power_limit",
        ),
        pytest.param(
            _line_network(_line(price=-0.1)),
            LINE,
            _line(price=-0.2),
            lambda network: network.optimize(),
            -0.5,
            -1.0,
            id="connection_price",
        ),
        pytest.param(
            _line_network(_line(efficiency=0.95)),
            LINE,
            _line(),
            lambda network: _line_segment(network, EfficiencySegment, "efficiency").efficiency,
            pytest.approx([0.95]),
            None,
            id="connection_efficiency_cleared",
        ),
        pytest.param(
            _battery_network(),
            BATTERY,
            _battery(min_charge=0.5),
            lambda network: _model_battery(network).charge_floor.tolist(),
            pytest.approx([2.0, 2.0]),
            pytest.approx([5.0, 5.0]),
            id="battery_min_charge",
        ),
        pytest.param(
            _battery_network(),
            BATTERY,
            _battery(max_charge=0.6),
            lambda network: _model_battery(network).charge_ceiling.tolist(),
            pytest.approx([9.0, 9.0]),
            pytest.approx([6.0, 6.0]),
            id="battery_max_charge",
        ),
        pytest.param(
            _battery_network(),
            BATTERY,
            _battery(charge_limit_cost=40.0),
            lambda network: _model_battery(network).charge_limit_cost.tolist(),
            pytest.approx([100.0]),
            pytest.approx([40.0]),
            id="battery_charge_limit_cost",
        ),
        pytest.param(
            # A negative salvage value drains the battery at its discharge limit, and the
            # discharge applies efficiency before the limit, so it draws limit / efficiency
            _battery_network(discharge_efficiency=0.8, salvage_value=-1.0),
            BATTERY,
            _battery(discharge_efficiency=0.5, salvage_value=-1.0),
            _discharge_drawn,
            pytest.approx(1.25),
            pytest.approx(2.0),
            id="battery_efficiency",
        ),
        pytest.param(
            {**_line_network(), POLICIES: _policies(0.07)},
            POLICIES,
            _policies(0.07, enabled=False),
            _policy_price,
            pytest.approx(0.07),
            0.0,
            id="policy_rule_disabled",
        ),
        pytest.param(
            {**_line_network(), POLICIES: _policies(0.07, enabled=False)},
            POLICIES,
            _policies(0.03),
            _policy_price,
            0.0,
            pytest.approx(0.03),
            id="policy_rule_enabled",
        ),
        pytest.param(
            {**_line_network(), POLICIES: _policies(0.07)},
            POLICIES,
            _policies(0.07, rules=0),
            _policy_price,
            pytest.approx(0.07),
            0.0,
            id="policy_rule_removed",
        ),
    ],
)
def test_updater_reaches_live_network(
    participants: dict[str, ElementConfigData],
    edited: str,
    edit: ElementConfigData,
    observe: Callable[[Network], object],
    before: object,
    after: object,
) -> None:
    """An element's updater applies its edited config to the network it was built with, without a rebuild."""
    network = build_network("test", participants, [3600])
    updaters = build_element_updaters(network, participants)
    elements = dict(network.elements)
    assert observe(network) == before

    updaters[edited](edit)

    assert observe(network) == after
    assert network.elements == elements


def test_policy_updater_rejects_another_element_type() -> None:
    """The policy element's updater fails loudly when given another element's config."""
    participants = {**_line_network(), POLICIES: _policies(0.07)}
    updaters = build_element_updaters(build_network("test", participants, [3600]), participants)

    with pytest.raises(TypeError, match="received a connection config"):
        updaters[POLICIES](_line())


def test_build_network_adds_every_element_in_hours() -> None:
    """Every configured element is added, with connections after the elements they join, over periods in hours."""
    load: LoadConfigData = {
        "element_type": ElementType.LOAD,
        "name": "Baseload",
        "connection": as_connection_target(SINK),
        "forecast": {"forecast": np.asarray([2.5, 2.5, 2.5, 2.5], dtype=float)},
        "curtailment": {},
    }
    participants: dict[str, ElementConfigData] = {LINE: _line(), **_line_network(), "Baseload": load}

    network = build_network("test", participants, [1800] * 4)
    updaters = build_element_updaters(network, participants)

    np.testing.assert_array_equal(network.periods, [0.5] * 4)
    assert list(network.elements)[-1] == LINE
    assert {SOURCE, SINK, LINE, "Baseload"} <= network.elements.keys()
    assert updaters.keys() == participants.keys()


def test_build_network_without_participants_is_empty() -> None:
    """A hub with no elements builds an empty network."""
    network = build_network("empty", {}, [1800])
    updaters = build_element_updaters(network, {})

    assert network.name == "empty"
    assert network.elements == {}
    assert updaters == {}


def test_build_network_tags_policied_flows() -> None:
    """A policy's source and target tag the flows it prices."""
    network = build_network("test", {**_line_network(), POLICIES: _policies(0.07)}, [900])

    line = network.elements[LINE]
    assert isinstance(line, Connection)
    # The source is the only one and is policied, so the line only carries its tag
    assert line.connection_tags() == {1}


def test_build_network_rejects_more_than_one_policy_element() -> None:
    """The config flow allows one policy element, so a second fails loudly."""
    participants: dict[str, ElementConfigData] = {
        **_line_network(),
        POLICIES: _policies(0.07),
        "More policies": {**_policies(0.02), "name": "More policies"},
    }

    with pytest.raises(ValueError, match="at most one policy element, found 2"):
        build_network("test", participants, [900])


def test_build_network_names_the_element_it_cannot_add(monkeypatch: pytest.MonkeyPatch) -> None:
    """A model element that cannot be added fails with its name."""

    def _raise(*_: object, **__: object) -> None:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setattr(Network, "add", _raise)

    with pytest.raises(ValueError, match=f"Failed to add model element '{SOURCE}'"):
        build_network("test", {SOURCE: _node(SOURCE, is_source=True, is_sink=False)}, [900])


def test_periods_in_hours() -> None:
    """Period durations convert from seconds to hours."""
    np.testing.assert_array_equal(periods_in_hours([900, 3600, 7200]), [0.25, 1.0, 2.0])

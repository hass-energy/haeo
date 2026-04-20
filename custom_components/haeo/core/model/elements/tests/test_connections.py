"""Model connection output tests covering reporting and validation helpers."""

from typing import Any, TypeGuard, cast

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import SOURCE_PENALTY_FACTOR, Connection
from custom_components.haeo.core.model.elements.segments.power_limit import PowerLimitSegment
from custom_components.haeo.core.model.elements.segments.pricing import PricingSegment
from custom_components.haeo.core.model.output_data import ModelOutputValue, OutputData
from custom_components.haeo.core.model.tests import test_data
from custom_components.haeo.core.model.tests.test_data.connection_types import (
    ConnectionTestCase,
    ConnectionTestCaseInputs,
    ExpectedOutput,
    ExpectedOutputFixture,
    ExpectedOutputs,
)


def _serialize_output_value(output_value: ModelOutputValue) -> ExpectedOutputFixture:
    if isinstance(output_value, OutputData):
        if output_value.unit is None:
            msg = "Expected unit for connection output"
            raise ValueError(msg)
        output: ExpectedOutput = {
            "type": output_value.type,
            "unit": output_value.unit,
            "values": tuple(float(value) for value in output_value.values),
        }
        return output
    return {name: _serialize_output_value(child) for name, child in output_value.items()}


class DummyElement(Element[str]):
    """Minimal element for connection endpoint wiring in tests.

    Acts as both source and sink so connections wired between two
    ``DummyElement`` instances are treated as terminal by
    :pyattr:`Connection.is_terminal` and therefore receive the
    time-preference secondary incentive.  Tests that need transfer-only
    behaviour set ``is_source`` / ``is_sink`` explicitly.
    """

    is_source: bool = True
    is_sink: bool = True

    def __init__(
        self,
        name: str,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        is_source: bool = True,
        is_sink: bool = True,
    ) -> None:
        """Create a dummy element with no outputs."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())
        self.is_source = is_source
        self.is_sink = is_sink


def _solve_connection_scenario(element: Connection[str], inputs: ConnectionTestCaseInputs | None) -> ExpectedOutputs:
    """Set up and solve an optimization scenario for a unidirectional connection."""
    h = element._solver
    source = DummyElement(element.source, element.periods, h)
    target = DummyElement(element.target, element.periods, h)
    element.set_endpoints(source, target)
    element.constraints()

    if inputs is None:
        h.run()
        outputs = element.outputs()
        return {name: _serialize_output_value(output_data) for name, output_data in outputs.items()}

    n_periods = element.n_periods
    periods = element.periods

    cost_terms: list[highs_linear_expression] = []

    if "fix_power_in" in inputs:
        values = inputs["fix_power_in"]
        total_power_in = element.total_power_in
        for i, val in enumerate(values):
            h.addConstr(total_power_in[i] == val)

    if inputs.get("maximize_power_out"):
        total_power_out = element.total_power_out
        cost_terms.append(-Highs.qsum(total_power_out[i] * periods[i] for i in range(n_periods)))

    # Collect primary cost from element (index 0 only, skip secondary time preference)
    element_cost = element.cost()
    if element_cost[0] is not None:
        cost_terms.append(element_cost[0])

    if cost_terms:
        h.minimize(Highs.qsum(cost_terms))
    h.run()

    outputs = element.outputs()
    return {name: _serialize_output_value(output_data) for name, output_data in outputs.items()}


def _is_expected_output(value: ExpectedOutputFixture) -> TypeGuard[ExpectedOutput]:
    return {"type", "unit", "values"}.issubset(value.keys())


def _assert_outputs_match(actual: ExpectedOutputFixture, expected: ExpectedOutputFixture) -> None:
    if _is_expected_output(expected):
        assert _is_expected_output(actual)
        assert actual["type"] == expected["type"]
        assert actual["unit"] == expected["unit"]
        tol = (2e-4, 2e-4) if expected["type"] == "shadow_price" else (1e-9, 1e-9)
        assert actual["values"] == pytest.approx(expected["values"], rel=tol[0], abs=tol[1])
        return

    assert not _is_expected_output(actual)
    actual_map = cast("ExpectedOutputs", actual)
    expected_map = cast("ExpectedOutputs", expected)
    for output_name, expected_value in expected_map.items():
        assert output_name in actual_map, f"Missing expected key: {output_name}"
        _assert_outputs_match(actual_map[output_name], expected_value)


@pytest.mark.parametrize(
    "case",
    test_data.VALID_CONNECTION_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_connection_outputs(case: ConnectionTestCase, solver: Highs) -> None:
    """Connection outputs should match expected values for unidirectional flows."""
    factory = case["factory"]
    data = case["data"].copy()
    data["solver"] = solver
    element = factory(**data)
    assert isinstance(element, Connection)

    outputs = _solve_connection_scenario(element, case.get("inputs"))

    assert "expected_outputs" in case
    expected_outputs = case["expected_outputs"]
    _assert_outputs_match(outputs, expected_outputs)


@pytest.mark.parametrize(
    "case",
    test_data.INVALID_CONNECTION_CASES,
    ids=lambda case: case["description"].lower().replace(" ", "_"),
)
def test_connection_validation(case: ConnectionTestCase, solver: Highs) -> None:
    """Connection classes should validate input sequence lengths match n_periods."""
    assert "expected_error" in case
    data = case["data"].copy()
    data["solver"] = solver
    with pytest.raises(ValueError, match=case["expected_error"]):
        case["factory"](**data)


def test_connection_power_properties(solver: Highs) -> None:
    """Connection power_in, power_out, power_into_source, power_into_target."""
    conn: Connection[str] = Connection(
        name="test_conn",
        periods=np.array([1.0, 1.0]),
        solver=solver,
        source="source_element",
        target="target_element",
    )
    source = DummyElement("source_element", conn.periods, solver)
    target = DummyElement("target_element", conn.periods, solver)
    conn.set_endpoints(source, target)
    conn.constraints()

    total_in = conn.total_power_in
    solver.addConstr(total_in[0] == 5.0)
    solver.addConstr(total_in[1] == 3.0)

    solver.run()

    power_in = [solver.val(total_in[i]) for i in range(2)]
    assert power_in == pytest.approx([5.0, 3.0])

    total_out = conn.total_power_out
    power_out = [solver.val(total_out[i]) for i in range(2)]
    assert power_out == pytest.approx([5.0, 3.0])

    power_into_source = [solver.val(conn.power_into_source[i]) for i in range(2)]
    assert power_into_source == pytest.approx([-5.0, -3.0])

    power_into_target = [solver.val(conn.power_into_target[i]) for i in range(2)]
    assert power_into_target == pytest.approx([5.0, 3.0])

    assert conn.source == "source_element"
    assert conn.target == "target_element"


def test_connection_getitem_integer_index(solver: Highs) -> None:
    """Connection supports integer indexing into segments."""
    conn: Connection[str] = Connection(
        name="idx_conn",
        periods=np.array([1.0]),
        solver=solver,
        source="a",
        target="b",
        segments={
            "power_limit": {"segment_type": "power_limit", "max_power": 5.0},
            "pricing": {"segment_type": "pricing", "price": 0.10},
        },
    )
    source = DummyElement("a", conn.periods, solver)
    target = DummyElement("b", conn.periods, solver)
    conn.set_endpoints(source, target)

    assert isinstance(conn[0], PowerLimitSegment)
    assert isinstance(conn[1], PricingSegment)
    assert conn["power_limit"] is conn[0]

    with pytest.raises(KeyError, match="No segment at index"):
        conn[99]


def test_connection_getitem_fallback(solver: Highs) -> None:
    """Connection falls back to Element.__getitem__ for unknown keys."""
    conn: Connection[str] = Connection(
        name="fallback_conn",
        periods=np.array([1.0]),
        solver=solver,
        source="a",
        target="b",
    )
    source = DummyElement("a", conn.periods, solver)
    target = DummyElement("b", conn.periods, solver)
    conn.set_endpoints(source, target)

    with pytest.raises(KeyError):
        conn["nonexistent_key"]


def test_connection_multiple_cost_sources(solver: Highs) -> None:
    """Connection aggregates costs from multiple segments."""
    conn: Connection[str] = Connection(
        name="multi_cost",
        periods=np.array([1.0]),
        solver=solver,
        source="a",
        target="b",
        segments={
            "pricing1": {"segment_type": "pricing", "price": 0.10},
            "pricing2": {"segment_type": "pricing", "price": 0.20},
        },
    )
    source = DummyElement("a", conn.periods, solver)
    target = DummyElement("b", conn.periods, solver)
    conn.set_endpoints(source, target)
    conn.constraints()

    cost = conn.cost()
    assert cost is not None
    assert cost[0] is not None

    solver.addConstr(conn.total_power_in[0] == 5.0)
    solver.minimize(cost[0])
    # Cost = 5 kW * (0.10 + 0.20) $/kWh * 1 h = 1.50
    assert solver.getObjectiveValue() == pytest.approx(1.50)


def test_connection_tag_cost_ignores_unknown_tag_and_missing_price(solver: Highs) -> None:
    """Per-tag policy costs skip tags not on the connection and rows without price."""
    conn: Connection[str] = Connection(
        name="tag_cost_skip",
        periods=np.array([1.0]),
        solver=solver,
        source="a",
        target="b",
        tags={1},
        tag_costs=[
            {"tag": 999, "price": 0.99},
            {"tag": 1},
            {"tag": 1, "price": 0.10},
        ],
        segments={"pl": {"segment_type": "power_limit", "max_power": 10.0}},
    )
    source = DummyElement("a", conn.periods, solver)
    target = DummyElement("b", conn.periods, solver)
    conn.set_endpoints(source, target)
    conn.constraints()

    cost = conn.cost()
    assert cost is not None
    assert cost[0] is not None

    solver.addConstr(conn.total_power_in[0] == 4.0)
    solver.minimize(cost[0])
    assert solver.getObjectiveValue() == pytest.approx(0.40)


def _probe_weights(n: int, *, is_source: bool, is_sink: bool) -> list[float]:
    """Recover per-period secondary weights for a single connection.

    Builds a standalone solver, places one unit of flow in period t and
    zero elsewhere, and reads off the secondary objective value at the
    optimum — which is exactly the secondary weight for that period.
    """
    values: list[float] = []
    for t in range(n):
        s = Highs()
        s.setOptionValue("output_flag", False)
        probe: Connection[str] = Connection(
            name="probe",
            periods=np.array([1.0] * n),
            solver=s,
            source="a",
            target="b",
            segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
        )
        probe.set_endpoints(
            DummyElement("a", probe.periods, s, is_source=is_source, is_sink=False),
            DummyElement("b", probe.periods, s, is_source=False, is_sink=is_sink),
        )
        probe.constraints()
        probe.priority = 0
        probe.priority_total = 1
        _, sec = probe.cost()
        assert sec is not None
        for i in range(n):
            s.addConstr(probe.total_power_in[i] == (1.0 if i == t else 0.0))
        s.minimize(sec)
        values.append(s.getObjectiveValue())
    return values


def test_sink_connection_has_strictly_negative_weights() -> None:
    """A sink-only terminal connection rewards any flow, earliest most.

    The secondary is minimised, so negative weights turn every unit of
    sink-arriving flow into a gain — earlier periods pay more, keeping
    the deterministic "fill earliest first" tie-breaker.
    """
    n = 3
    weights = _probe_weights(n, is_source=False, is_sink=True)

    # priority=0, priority_total=1 -> raw=[1,2,3], offset=1*3+1=4
    # -> magnitude=[3,2,1], sink weights = -magnitude.
    assert all(w < 0.0 for w in weights), weights
    assert weights == pytest.approx([-3.0, -2.0, -1.0])


def test_source_connection_has_strictly_positive_weights() -> None:
    """A source-only terminal connection penalises early production.

    Every unit of flow leaving a source adds a positive secondary cost,
    decreasing with time so the solver prefers to defer production to
    later periods.  Magnitude is scaled down by ``SOURCE_PENALTY_FACTOR``
    so the sink-side reward on the far end of any real path still
    dominates and overall flow is incentivised.
    """
    n = 3
    weights = _probe_weights(n, is_source=True, is_sink=False)

    # Same magnitude schedule as the sink side but flipped sign and
    # scaled by SOURCE_PENALTY_FACTOR.
    assert all(w > 0.0 for w in weights), weights
    assert weights == pytest.approx(
        [
            3.0 * SOURCE_PENALTY_FACTOR,
            2.0 * SOURCE_PENALTY_FACTOR,
            1.0 * SOURCE_PENALTY_FACTOR,
        ]
    )


def test_source_and_sink_connection_partially_cancels() -> None:
    """When both ends are terminal the two weights partly cancel.

    A battery-to-battery (round-trip-on-one-element) style connection
    has both ``is_sink`` and ``is_source`` on its endpoints.  The net
    secondary weight per period is
    ``-magnitude + magnitude * SOURCE_PENALTY_FACTOR``: still negative
    (so genuine flow is still slightly rewarded) but much smaller in
    magnitude than a sink-only connection — this is what prevents
    phantom round-trip flow from being doubly rewarded.
    """
    n = 3
    weights = _probe_weights(n, is_source=True, is_sink=True)

    # magnitude=[3,2,1]; net = magnitude * (SOURCE_PENALTY_FACTOR - 1).
    expected = [m * (SOURCE_PENALTY_FACTOR - 1.0) for m in (3.0, 2.0, 1.0)]
    assert weights == pytest.approx(expected)
    # Sanity: sink-only reward is strictly stronger than the both-sided
    # combined reward — genuine flow is preferred over round-trip.
    sink_only = _probe_weights(n, is_source=False, is_sink=True)
    for both, sink in zip(weights, sink_only, strict=True):
        assert abs(both) < abs(sink)


def test_sink_connection_preserves_time_order(solver: Highs) -> None:
    """Earlier periods get more negative weights than later ones.

    Given unit capacity per period and no primary cost, minimising the
    secondary must pack flow into the earliest periods first.
    """
    periods = np.array([1.0, 1.0, 1.0, 1.0])
    conn: Connection[str] = Connection(
        name="ordered",
        periods=periods,
        solver=solver,
        source="a",
        target="b",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    conn.set_endpoints(
        DummyElement("a", periods, solver, is_source=False, is_sink=False),
        DummyElement("b", periods, solver, is_source=False, is_sink=True),
    )
    conn.priority = 0
    conn.priority_total = 1
    conn.constraints()

    _, secondary = conn.cost()
    assert secondary is not None
    # Bound total flow to 2 kWh so the solver must choose 2 of 4 periods.
    solver.addConstr(Highs.qsum(conn.total_power_in[i] for i in range(4)) == 2.0)
    solver.minimize(secondary)

    values = [solver.val(conn.total_power_in[i]) for i in range(4)]
    # Earliest two periods should be filled first.
    assert values[0] == pytest.approx(1.0)
    assert values[1] == pytest.approx(1.0)
    assert values[2] == pytest.approx(0.0)
    assert values[3] == pytest.approx(0.0)


def test_source_connection_prefers_later_flow(solver: Highs) -> None:
    """A source-only connection with a fixed flow budget is shifted late.

    Positive weights decreasing over time penalise early production, so
    when the solver must place a fixed total flow, it defers it to the
    latest periods.
    """
    periods = np.array([1.0, 1.0, 1.0, 1.0])
    conn: Connection[str] = Connection(
        name="deferred",
        periods=periods,
        solver=solver,
        source="a",
        target="b",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    conn.set_endpoints(
        DummyElement("a", periods, solver, is_source=True, is_sink=False),
        DummyElement("b", periods, solver, is_source=False, is_sink=False),
    )
    conn.priority = 0
    conn.priority_total = 1
    conn.constraints()

    _, secondary = conn.cost()
    assert secondary is not None
    solver.addConstr(Highs.qsum(conn.total_power_in[i] for i in range(4)) == 2.0)
    solver.minimize(secondary)

    values = [solver.val(conn.total_power_in[i]) for i in range(4)]
    # Latest two periods should be filled first for sources.
    assert values[0] == pytest.approx(0.0)
    assert values[1] == pytest.approx(0.0)
    assert values[2] == pytest.approx(1.0)
    assert values[3] == pytest.approx(1.0)


def test_connection_secondary_respects_priority(solver: Highs) -> None:
    """Lower-priority sink connections fill before higher-priority ones.

    Two single-period connections share a common per-period capacity
    budget: minimising the combined secondary must pick the
    lower-priority connection first.
    """
    periods = np.array([1.0])
    low: Connection[str] = Connection(
        name="low_prio",
        periods=periods,
        solver=solver,
        source="src_a",
        target="dst_a",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    high: Connection[str] = Connection(
        name="high_prio",
        periods=periods,
        solver=solver,
        source="src_b",
        target="dst_b",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    low.set_endpoints(
        DummyElement("src_a", periods, solver, is_source=False, is_sink=False),
        DummyElement("dst_a", periods, solver, is_source=False, is_sink=True),
    )
    high.set_endpoints(
        DummyElement("src_b", periods, solver, is_source=False, is_sink=False),
        DummyElement("dst_b", periods, solver, is_source=False, is_sink=True),
    )
    low.constraints()
    high.constraints()
    low.priority = 0
    high.priority = 1
    low.priority_total = 2
    high.priority_total = 2

    _, sec_low = low.cost()
    _, sec_high = high.cost()
    assert sec_low is not None
    assert sec_high is not None
    # Shared total budget of 1 kWh across both connections.
    solver.addConstr(low.total_power_in[0] + high.total_power_in[0] == 1.0)
    solver.minimize(Highs.qsum([sec_low, sec_high]))

    assert solver.val(low.total_power_in[0]) == pytest.approx(1.0)
    assert solver.val(high.total_power_in[0]) == pytest.approx(0.0)


def test_round_trip_pair_reduces_secondary_reward(solver: Highs) -> None:
    """A paired sink + source connection (battery-style) partly cancels.

    Models a battery-charge (sink-only) + battery-discharge (source-only)
    pair where both carry one unit of flow in the same period — this is
    exactly the phantom "round-trip" that the old uniformly-negative
    weight scheme double-rewarded.  The combined cost under the new
    scheme must be strictly weaker in magnitude than under the old
    scheme (both legs negative), so the solver no longer has a
    disproportionate incentive to round-trip power through a battery.
    """
    periods = np.array([1.0])
    sink_only: Connection[str] = Connection(
        name="charge",
        periods=periods,
        solver=solver,
        source="inverter",
        target="battery",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    source_only: Connection[str] = Connection(
        name="discharge",
        periods=periods,
        solver=solver,
        source="battery",
        target="inverter",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    sink_only.set_endpoints(
        DummyElement("inverter", periods, solver, is_source=False, is_sink=False),
        DummyElement("battery_sink", periods, solver, is_source=False, is_sink=True),
    )
    source_only.set_endpoints(
        DummyElement("battery_source", periods, solver, is_source=True, is_sink=False),
        DummyElement("inverter_2", periods, solver, is_source=False, is_sink=False),
    )
    for c, p in ((sink_only, 0), (source_only, 1)):
        c.constraints()
        c.priority = p
        c.priority_total = 2

    _, sec_sink = sink_only.cost()
    _, sec_source = source_only.cost()
    assert sec_sink is not None
    assert sec_source is not None

    solver.addConstr(sink_only.total_power_in[0] == 1.0)
    solver.addConstr(source_only.total_power_in[0] == 1.0)
    solver.minimize(Highs.qsum([sec_sink, sec_source]))

    combined = solver.getObjectiveValue()

    # Magnitudes per the priority schedule (priority_total=2, n=1):
    # sink (priority 0):   raw=1, offset=3 -> magnitude=2 -> weight=-2
    # source (priority 1): raw=2, offset=3 -> magnitude=1 -> weight=+0.5
    # Combined for 1 kWh each: -2 + 0.5 = -1.5
    expected_new = -2.0 + 1.0 * SOURCE_PENALTY_FACTOR
    assert combined == pytest.approx(expected_new)

    # The "old scheme" (both connections uniformly negative) would have
    # combined to -2 + -1 = -3.  Under the new scheme the absolute
    # magnitude must be strictly smaller — this is the property that
    # removes the double reward and deters phantom round-tripping.
    old_scheme = -2.0 - 1.0
    assert abs(combined) < abs(old_scheme)


def test_connection_is_terminal_requires_source_or_sink(solver: Highs) -> None:
    """``is_terminal`` follows endpoint ``is_source`` / ``is_sink`` flags."""
    periods = np.array([1.0])
    conn: Connection[str] = Connection(
        name="probe",
        periods=periods,
        solver=solver,
        source="src",
        target="tgt",
    )

    # No endpoints wired yet -> neutral (non-terminal).
    assert conn.is_terminal is False

    src = DummyElement("src", periods, solver, is_source=False, is_sink=False)
    tgt = DummyElement("tgt", periods, solver, is_source=False, is_sink=False)
    conn.set_endpoints(src, tgt)

    # Transfer endpoints -> non-terminal.
    assert conn.is_terminal is False

    # Either endpoint matching is sufficient.
    src.is_source = True
    assert conn.is_terminal is True

    src.is_source = False
    tgt.is_sink = True
    assert conn.is_terminal is True


def test_connection_non_terminal_has_no_secondary(solver: Highs) -> None:
    """Transfer-only connections must not receive the negative secondary incentive.

    Without this guard the solver would happily saturate any zero-primary-cost
    loop (e.g. an inverter's DC↔AC pair) to consume the secondary budget.
    """
    periods = np.array([1.0, 1.0, 1.0])
    conn: Connection[str] = Connection(
        name="transfer",
        periods=periods,
        solver=solver,
        source="src",
        target="tgt",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    src = DummyElement("src", periods, solver, is_source=False, is_sink=False)
    tgt = DummyElement("tgt", periods, solver, is_source=False, is_sink=False)
    conn.set_endpoints(src, tgt)
    conn.constraints()
    conn.priority = 0
    conn.priority_total = 1

    primary, secondary = conn.cost()

    # No pricing segments -> no primary either.
    assert primary is None
    assert secondary is None


def test_non_terminal_transfer_does_not_steal_secondary_budget(solver: Highs) -> None:
    """A zero-primary-cost transfer loop must not out-bid a terminal sink.

    Two parallel capacity-1 paths feed a sink:
      * ``terminal`` from source -> sink (gets the secondary incentive)
      * ``transfer`` from junction -> junction (must NOT get one)

    A shared budget of 1 kWh must land on the terminal connection, because
    only terminal connections carry negative secondary weight.  Prior to the
    terminal gating, the transfer connection would have tied on secondary
    cost and pulled the budget away from the useful path.
    """
    periods = np.array([1.0])
    terminal: Connection[str] = Connection(
        name="terminal",
        periods=periods,
        solver=solver,
        source="source_node",
        target="sink_node",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    transfer: Connection[str] = Connection(
        name="transfer",
        periods=periods,
        solver=solver,
        source="junction_a",
        target="junction_b",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    terminal.set_endpoints(
        DummyElement("source_node", periods, solver, is_source=True, is_sink=False),
        DummyElement("sink_node", periods, solver, is_source=False, is_sink=True),
    )
    transfer.set_endpoints(
        DummyElement("junction_a", periods, solver, is_source=False, is_sink=False),
        DummyElement("junction_b", periods, solver, is_source=False, is_sink=False),
    )
    terminal.constraints()
    transfer.constraints()
    terminal.priority = 0
    transfer.priority = 1
    terminal.priority_total = 2
    transfer.priority_total = 2

    _, sec_terminal = terminal.cost()
    _, sec_transfer = transfer.cost()

    assert sec_transfer is None
    assert sec_terminal is not None

    # Shared flow budget of 1 kWh; minimising only the terminal secondary
    # (since transfer has none) should push all the flow through terminal.
    solver.addConstr(terminal.total_power_in[0] + transfer.total_power_in[0] == 1.0)
    solver.minimize(sec_terminal)

    assert solver.val(terminal.total_power_in[0]) == pytest.approx(1.0)
    assert solver.val(transfer.total_power_in[0]) == pytest.approx(0.0)

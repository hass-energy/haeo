"""Model connection output tests covering reporting and validation helpers."""

from typing import Any, TypeGuard, cast

from highspy import Highs
from highspy.highs import highs_linear_expression
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
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
    """Minimal element for connection endpoint wiring in tests."""

    def __init__(self, name: str, periods: NDArray[np.floating[Any]], solver: Highs) -> None:
        """Create a dummy element with no outputs."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


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


def test_connection_secondary_weights_strictly_negative(solver: Highs) -> None:
    """Time-preference secondary coefficients must all be < 0.

    The secondary objective is minimised, so negative weights turn it
    into a gentle incentive to carry flow (earlier first) rather than a
    penalty that drives flow to zero at cost parity.
    """
    n = 3
    conn: Connection[str] = Connection(
        name="neg_weights",
        periods=np.array([1.0] * n),
        solver=solver,
        source="a",
        target="b",
        segments={"pl": {"segment_type": "power_limit", "max_power": 1.0}},
    )
    conn.set_endpoints(DummyElement("a", conn.periods, solver), DummyElement("b", conn.periods, solver))
    conn.constraints()
    conn.priority = 0
    conn.priority_total = 1  # single-connection network

    _, secondary = conn.cost()

    # Recover each per-period weight by solving with exactly one unit of
    # flow placed in period t and zero elsewhere.
    def _weight_at(t: int) -> float:
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
        probe.set_endpoints(DummyElement("a", probe.periods, s), DummyElement("b", probe.periods, s))
        probe.constraints()
        probe.priority = 0
        probe.priority_total = 1
        _, sec = probe.cost()
        for i in range(n):
            s.addConstr(probe.total_power_in[i] == (1.0 if i == t else 0.0))
        s.minimize(sec)
        return s.getObjectiveValue()

    weights = [_weight_at(t) for t in range(n)]
    assert all(w < 0.0 for w in weights), weights
    # priority=0, priority_total=1 -> raw=[1,2,3], offset = 1*3+1 = 4
    # -> weights=[-3,-2,-1]
    assert weights == pytest.approx([-3.0, -2.0, -1.0])

    # Silence unused-secondary warning — the expression is used above
    # via probe cost(); assert it exists on the original connection too.
    assert secondary is not None


def test_connection_secondary_preserves_time_order(solver: Highs) -> None:
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
    source = DummyElement("a", periods, solver)
    target = DummyElement("b", periods, solver)
    conn.set_endpoints(source, target)
    conn.priority = 0
    conn.priority_total = 1
    conn.constraints()

    _, secondary = conn.cost()
    # Bound total flow to 2 kWh so the solver must choose 2 of 4 periods.
    solver.addConstr(Highs.qsum(conn.total_power_in[i] for i in range(4)) == 2.0)
    solver.minimize(secondary)

    values = [solver.val(conn.total_power_in[i]) for i in range(4)]
    # Earliest two periods should be filled first.
    assert values[0] == pytest.approx(1.0)
    assert values[1] == pytest.approx(1.0)
    assert values[2] == pytest.approx(0.0)
    assert values[3] == pytest.approx(0.0)


def test_connection_secondary_respects_priority(solver: Highs) -> None:
    """Lower-priority connections fill before higher-priority ones.

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
    low.set_endpoints(DummyElement("src_a", periods, solver), DummyElement("dst_a", periods, solver))
    high.set_endpoints(DummyElement("src_b", periods, solver), DummyElement("dst_b", periods, solver))
    low.constraints()
    high.constraints()
    low.priority = 0
    high.priority = 1
    low.priority_total = 2
    high.priority_total = 2

    _, sec_low = low.cost()
    _, sec_high = high.cost()
    # Shared total budget of 1 kWh across both connections.
    solver.addConstr(low.total_power_in[0] + high.total_power_in[0] == 1.0)
    solver.minimize(Highs.qsum([sec_low, sec_high]))

    assert solver.val(low.total_power_in[0]) == pytest.approx(1.0)
    assert solver.val(high.total_power_in[0]) == pytest.approx(0.0)

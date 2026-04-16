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
    if element_cost is not None and element_cost[0] is not None:
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
        if expected["type"] == "shadow_price":
            assert actual["values"] == pytest.approx(expected["values"], rel=2e-4, abs=2e-4)
        else:
            assert actual["values"] == pytest.approx(expected["values"], rel=1e-9, abs=1e-9)
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

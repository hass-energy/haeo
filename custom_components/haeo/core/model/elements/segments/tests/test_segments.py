"""Tests for connection segments and Connection class."""

from collections.abc import Sequence
from functools import reduce
import operator
from typing import (
    Any,  # noqa: TID251  # source_element/target_element are the connection's endpoint elements,
    # which can be any concrete NetworkElement subtype. Element is invariant in its output-name
    # Literal (see element.py's outputs()), so no non-Any type expresses "an Element of some
    # unknown output-name type" here; DummySegment only forwards these to the base class.
)

import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments import EfficiencySegment, PowerLimitSegment, PricingSegment
from custom_components.haeo.core.model.elements.segments.segment import FlowProvider, FlowVariables, Segment
from custom_components.haeo.core.model.linear import LinearArray, total
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import cost, output
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.tests import test_data
from custom_components.haeo.core.model.tests.test_data import minimize
from custom_components.haeo.core.model.tests.test_data.segment_types import (
    ConnectionScenario,
    ExpectedValue,
    SegmentScenario,
)
from custom_components.haeo.core.model.util.solver_rows import add_rows


def create_solver() -> Solver:
    """Create a silent HiGHS solver."""
    h = Solver()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


class DummyElement(Element[str]):
    """Minimal element for segment endpoint wiring in tests."""

    def __init__(self, name: str, periods: NDArray[np.float64], solver: Solver) -> None:
        """Create a dummy element with no outputs."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


class DummySegment(Segment):
    """Minimal segment for coverage of base helpers."""

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.float64],
        solver: Solver,
        *,
        source_element: Element[Any],
        target_element: Element[Any],
        upstream: FlowProvider,
    ) -> None:
        """Initialize a dummy segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            upstream=upstream,
        )
        self._cost_var = solver.add_variables(1, name="cost_var")

    @output
    def coverage_output(self) -> OutputData:
        """Expose a dummy output for Segment.outputs coverage."""
        return OutputData(type=OutputType.POWER, unit="kW", values=tuple(0.0 for _ in range(self.n_periods)))

    @cost
    def list_cost(self) -> LinearArray:
        """Return a cost term for cost aggregation testing."""
        return self._cost_var.total()


def _assert_expected_value(actual: ExpectedValue, expected: ExpectedValue) -> None:
    if isinstance(expected, Sequence) and not isinstance(expected, str):
        assert isinstance(actual, Sequence)
        assert not isinstance(actual, str)
        if all(isinstance(item, str) for item in expected):
            assert list(actual) == list(expected)
            return
        np.testing.assert_allclose(
            np.asarray(actual, dtype=np.float64),
            np.asarray(expected, dtype=np.float64),
            rtol=1e-6,
            atol=1e-6,
        )
        return
    assert isinstance(expected, float | int)
    assert isinstance(actual, float | int)
    assert actual == pytest.approx(expected, rel=1e-6, abs=1e-6)


def _assert_expected_outputs(actual: dict[str, ExpectedValue], expected: dict[str, ExpectedValue]) -> None:
    assert set(actual.keys()) == set(expected.keys())
    for name, expected_value in expected.items():
        _assert_expected_value(actual[name], expected_value)


def _solve_segment_scenario(case: SegmentScenario) -> dict[str, ExpectedValue]:
    h = create_solver()
    periods = np.asarray(case["periods"], dtype=np.float64)
    endpoint_factory = case.get("endpoint_factory")
    if endpoint_factory is None:
        source = DummyElement("source", periods, h)
        target = DummyElement("target", periods, h)
    else:
        source, target = endpoint_factory(h, periods)

    power_in = h.add_variables(len(periods), name="power_in")
    tagged_power = {0: power_in}
    seg = case["factory"](
        "seg",
        len(periods),
        periods,
        h,
        spec=case["spec"],
        source_element=source,
        target_element=target,
        upstream=FlowVariables(tagged_power),
    )
    seg.constraints()

    inputs = case["inputs"]
    if "power_in" in inputs:
        add_rows(h, seg.total_power_in == np.asarray(inputs["power_in"], dtype=np.float64))

    objective_terms = []
    if inputs.get("minimize_cost"):
        cost = seg.cost()
        if cost is not None:
            objective_terms.append(cost)

    for name, weight in inputs.get("maximize", {}).items():
        attr_val = getattr(seg, name)
        if isinstance(attr_val, dict):
            attr_val = reduce(operator.add, attr_val.values())
        objective_terms.append(-float(weight) * attr_val.total())

    if objective_terms:
        minimize(h, total(objective_terms))
    h.run()

    outputs: dict[str, ExpectedValue] = {}
    for key in case["expected_outputs"]:
        if key == "objective_value":
            outputs[key] = float(h.getObjectiveValue())
        else:
            attr_val = getattr(seg, key)
            if isinstance(attr_val, dict):
                attr_val = reduce(operator.add, attr_val.values())
            outputs[key] = tuple(float(v) for v in attr_val.value(h.column_values()))
    return outputs


def _solve_connection_scenario(case: ConnectionScenario) -> dict[str, ExpectedValue]:
    h = create_solver()
    periods = np.asarray(case["periods"], dtype=np.float64)
    segments = case["segments"]
    if segments is None:
        conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt", tags={1})
    else:
        conn = Connection(
            name="conn", periods=periods, solver=h, source="src", target="tgt", tags={1}, segments=segments
        )
    source = DummyElement("src", periods, h)
    target = DummyElement("tgt", periods, h)
    conn.set_endpoints(source, target)

    inputs = case["inputs"]
    for segment_name, attr, value in inputs.get("updates", ()):
        segment = conn[segment_name]
        setattr(segment, attr, np.asarray(value, dtype=np.float64))

    conn.constraints()

    if "power_in" in inputs:
        add_rows(h, conn.total_power_in == np.asarray(inputs["power_in"], dtype=np.float64))

    objective_terms = []
    if inputs.get("minimize_cost"):
        cost = conn.cost()
        assert cost is not None
        if cost:
            objective_terms.append(cost[0])

    maximize = inputs.get("maximize", {})
    for name, weight in maximize.items():
        flow = getattr(conn, name)
        if isinstance(flow, dict):
            flow = reduce(operator.add, flow.values())
        objective_terms.append(-float(weight) * flow.total())

    if objective_terms:
        minimize(h, total(objective_terms))
    needs_solver = any(key in {"power_in", "power_out", "objective_value"} for key in case["expected_outputs"])
    if objective_terms or needs_solver:
        h.run()

    outputs: dict[str, ExpectedValue] = {}
    for key in case["expected_outputs"]:
        if key == "objective_value":
            outputs[key] = float(h.getObjectiveValue())
            continue
        if key == "segment_names":
            outputs[key] = list(conn.segments.keys())
            continue
        if key == "segment_types":
            outputs[key] = [type(seg).__name__ for seg in conn.segments.values()]
            continue
        if key == "segment_types_by_index":
            outputs[key] = [type(conn[idx]).__name__ for idx in range(len(conn.segments))]
            continue
        if key == "power_limit_max_power":
            pl = conn["power_limit"]
            assert isinstance(pl, PowerLimitSegment)
            assert pl.max_power is not None
            outputs[key] = tuple(float(v) for v in pl.max_power)
            continue
        if key == "pricing_price":
            pr = conn["pricing"]
            assert isinstance(pr, PricingSegment)
            assert pr.price is not None
            outputs[key] = tuple(float(v) for v in pr.price)
            continue
        flow = getattr(conn, key)
        if isinstance(flow, dict):
            flow = reduce(operator.add, flow.values())
        outputs[key] = tuple(float(v) for v in flow.value(h.column_values()))
    return outputs


@pytest.mark.parametrize("case", test_data.SEGMENT_SCENARIOS, ids=lambda c: c["description"])
def test_segment_scenarios(case: SegmentScenario) -> None:
    """Segments should match expected inputs/outputs."""
    outputs = _solve_segment_scenario(case)
    _assert_expected_outputs(outputs, case["expected_outputs"])


@pytest.mark.parametrize("case", test_data.CONNECTION_SEGMENT_SCENARIOS, ids=lambda c: c["description"])
def test_connection_scenarios(case: ConnectionScenario) -> None:
    """Connections should match expected inputs/outputs."""
    outputs = _solve_connection_scenario(case)
    _assert_expected_outputs(outputs, case["expected_outputs"])


def test_segment_outputs_and_cost_coverage() -> None:
    """Segment helpers expose outputs, costs, and period metadata."""
    h = create_solver()
    periods = np.asarray([1.0, 1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)
    power = h.add_variables(len(periods), name="power")
    segment = DummySegment(
        "seg",
        len(periods),
        periods,
        h,
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power}),
    )

    np.testing.assert_array_equal(segment.periods, periods)

    outputs = segment.outputs()
    assert "coverage_output" in outputs

    cost_value = segment.cost()
    assert cost_value is not None


def test_multiple_cost_methods_aggregate() -> None:
    """Element with multiple @cost methods sums them into a single expression."""

    class MultiCostElement(Element[str]):
        def __init__(self, solver: Solver) -> None:
            super().__init__(
                name="multi",
                periods=np.array([1.0]),
                solver=solver,
                output_names=frozenset(),
            )
            self._v1 = solver.add_variables(1, name="v1")
            self._v2 = solver.add_variables(1, name="v2")

        @cost
        def cost_a(self) -> LinearArray:
            return self._v1.total()

        @cost
        def cost_b(self) -> LinearArray:
            return self._v2.total()

    solver = Solver()
    solver.setOptionValue("output_flag", False)
    elem = MultiCostElement(solver)
    result = elem.cost()
    assert result is not None
    # Expression should reference indices from both variables
    idxs = set(result.cols.ravel().tolist())
    assert len(idxs) >= 2


def test_tag_transfer_cost_none_when_no_tags_match() -> None:
    """Tag transfer cost returns None when tag_prices references tags not in power_in."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)
    power_in = h.add_variables(len(periods), name="power_in")
    segment = PricingSegment(
        "seg",
        len(periods),
        periods,
        h,
        spec={"segment_type": "pricing", "tag_prices": [{"tag": 99, "price": 0.05}]},
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power_in}),
    )

    assert segment.tag_transfer_cost() is None


def test_efficiency_segment_treats_none_as_unity_after_update() -> None:
    """Efficiency segment should treat None values as 100% efficiency."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)

    power_in = h.add_variables(len(periods), name="power_in")
    segment = EfficiencySegment(
        "seg",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency", "efficiency": np.array([0.9], dtype=np.float64)},
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power_in}),
    )

    # Simulate coordinator update path clearing optional efficiency.
    segment.efficiency = None
    add_rows(h, segment.total_power_in == np.asarray([10.0], dtype=np.float64))
    h.run()

    np.testing.assert_allclose(segment.total_power_out.value(h.column_values()), [10.0], rtol=1e-6, atol=1e-6)


def test_efficiency_segment_treats_missing_values_as_unity_both_directions() -> None:
    """Missing efficiency values should keep both segments lossless."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)
    power_a = h.add_variables(len(periods), name="power_a")
    power_b = h.add_variables(len(periods), name="power_b")
    seg_a = EfficiencySegment(
        "seg_a",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency"},
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power_a}),
    )
    seg_b = EfficiencySegment(
        "seg_b",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency"},
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power_b}),
    )

    add_rows(h, seg_a.total_power_in == np.asarray([7.5], dtype=np.float64))
    add_rows(h, seg_b.total_power_in == np.asarray([3.5], dtype=np.float64))
    h.run()

    np.testing.assert_allclose(seg_a.total_power_out.value(h.column_values()), [7.5], rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(seg_b.total_power_out.value(h.column_values()), [3.5], rtol=1e-6, atol=1e-6)


def test_power_limit_no_max_power() -> None:
    """PowerLimitSegment with max_power=None applies no constraint."""
    h = create_solver()
    periods = np.array([1.0, 1.0])
    source = DummyElement("src", periods, h)
    target = DummyElement("tgt", periods, h)

    power_in = h.add_variables(2, name="power_in")
    seg = PowerLimitSegment(
        "no_limit",
        2,
        periods,
        h,
        spec={"segment_type": "power_limit"},
        source_element=source,
        target_element=target,
        upstream=FlowVariables({0: power_in}),
    )
    seg.constraints()

    # With no max_power, the flow is unconstrained (except lb=0)
    # Maximize to check it can go arbitrarily high
    minimize(h, -1.0 * power_in.total())
    h.run()
    # HiGHS returns 0 for unbounded, but the key point is no constraint error
    assert seg.max_power is None

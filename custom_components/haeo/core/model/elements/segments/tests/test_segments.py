"""Tests for connection segments and Connection class."""

from collections.abc import Sequence
from typing import Any

from highspy import Highs
from highspy.highs import HighspyArray, highs_linear_expression
import numpy as np
from numpy.typing import NDArray
import pytest

from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements.connection import Connection
from custom_components.haeo.core.model.elements.segments import (
    EfficiencySegment,
    PowerLimitSegment,
    PricingSegment,
    SocPricingSegment,
    is_efficiency_spec,
    is_passthrough_spec,
    is_power_limit_spec,
    is_pricing_spec,
    is_soc_pricing_spec,
)
from custom_components.haeo.core.model.elements.segments.segment import Segment
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import cost, output
from custom_components.haeo.core.model.tests import test_data
from custom_components.haeo.core.model.tests.test_data.segment_types import (
    ConnectionScenario,
    ExpectedValue,
    SegmentErrorScenario,
    SegmentScenario,
)


def create_solver() -> Highs:
    """Create a silent HiGHS solver."""
    h = Highs()
    h.setOptionValue("output_flag", False)
    h.setOptionValue("log_to_console", False)
    return h


class DummyElement(Element[str]):
    """Minimal element for segment endpoint wiring in tests."""

    def __init__(self, name: str, periods: NDArray[np.floating[Any]], solver: Highs) -> None:
        """Create a dummy element with no outputs."""
        super().__init__(name=name, periods=periods, solver=solver, output_names=frozenset())


class DummySegment(Segment):
    """Minimal segment for coverage of base helpers."""

    def __init__(
        self,
        segment_id: str,
        n_periods: int,
        periods: NDArray[np.floating[Any]],
        solver: Highs,
        *,
        source_element: Element[Any],
        target_element: Element[Any],
        power_in: HighspyArray,
    ) -> None:
        """Initialize a dummy segment."""
        super().__init__(
            segment_id,
            n_periods,
            periods,
            solver,
            source_element=source_element,
            target_element=target_element,
            power_in=power_in,
        )
        self._cost_var = solver.addVariables(1, lb=0, name_prefix=f"{segment_id}_c_", out_array=True)

    @output
    def coverage_output(self) -> OutputData:
        """Expose a dummy output for Segment.outputs coverage."""
        return OutputData(type=OutputType.POWER, unit="kW", values=tuple(0.0 for _ in range(self.n_periods)))

    @cost
    def list_cost(self) -> list[highs_linear_expression]:
        """Return multiple cost terms to exercise cost aggregation."""
        return [
            Highs.qsum(self._cost_var),
            Highs.qsum(self._cost_var),
        ]


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
    # Create variables and pass to segment (single direction - "st" for testing)
    n = len(periods)
    power_st = h.addVariables(n, lb=0, name_prefix="test_st_", out_array=True)
    power_ts = h.addVariables(n, lb=0, name_prefix="test_ts_", out_array=True)

    # Create st-direction segment
    seg_st = case["factory"](
        "seg_st",
        len(periods),
        periods,
        h,
        spec=case["spec"],
        source_element=source,
        target_element=target,
        power_in=power_st,
    )
    seg_st.constraints()

    # Create ts-direction segment only if test uses ts inputs/outputs
    inputs = case["inputs"]
    expected_outputs = case["expected_outputs"]
    needs_ts = any(k.endswith("_ts") for k in (*inputs, *expected_outputs, *inputs.get("maximize", {})))
    seg_ts = None
    if needs_ts or "power_in_ts" in inputs:
        seg_ts = case["factory"](
            "seg_ts",
            len(periods),
            periods,
            h,
            spec=case["spec"],
            source_element=source,
            target_element=target,
            power_in=power_ts,
        )
        seg_ts.constraints()

    inputs = case["inputs"]
    if "power_in_st" in inputs:
        h.addConstrs(seg_st.power_in == np.asarray(inputs["power_in_st"], dtype=np.float64))
    if "power_in_ts" in inputs and seg_ts is not None:
        h.addConstrs(seg_ts.power_in == np.asarray(inputs["power_in_ts"], dtype=np.float64))

    objective_terms = []
    if inputs.get("minimize_cost"):
        c = seg_st.cost()
        if c is not None:
            objective_terms.append(c)
        if seg_ts is not None:
            c = seg_ts.cost()
            if c is not None:
                objective_terms.append(c)

    maximize = inputs.get("maximize", {})
    for name, weight in maximize.items():
        if name.endswith("_st"):
            attr = name.removesuffix("_st")
            flow = getattr(seg_st, attr)
        elif name.endswith("_ts"):
            attr = name.removesuffix("_ts")
            flow = getattr(seg_ts, attr)
        else:
            flow = getattr(seg_st, name)
        objective_terms.append(-float(weight) * Highs.qsum(flow))

    if objective_terms:
        h.minimize(Highs.qsum(objective_terms))
    h.run()

    expected_outputs = case["expected_outputs"]
    outputs: dict[str, ExpectedValue] = {}
    for key in expected_outputs:
        if key == "objective_value":
            outputs[key] = float(h.getObjectiveValue())
            continue
        # Map directional keys to the correct single-direction segment
        if key.endswith("_st"):
            attr = key.removesuffix("_st")
            flow = getattr(seg_st, attr.replace("power_in", "power_in").replace("power_out", "power_out"))
        elif key.endswith("_ts"):
            attr = key.removesuffix("_ts")
            flow = getattr(seg_ts, attr.replace("power_in", "power_in").replace("power_out", "power_out"))
        else:
            flow = getattr(seg_st, key)
        outputs[key] = tuple(float(value) for value in h.vals(flow))
    return outputs


def _solve_connection_scenario(case: ConnectionScenario) -> dict[str, ExpectedValue]:
    h = create_solver()
    periods = np.asarray(case["periods"], dtype=np.float64)
    segments = case["segments"]
    if segments is None:
        conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt")
    else:
        conn = Connection(name="conn", periods=periods, solver=h, source="src", target="tgt", segments=segments)
    source = DummyElement("src", periods, h)
    target = DummyElement("tgt", periods, h)
    conn.set_endpoints(source, target)

    inputs = case["inputs"]
    for segment_name, attr, value in inputs.get("updates", ()):
        segment = conn[segment_name]
        setattr(segment, attr, np.asarray(value, dtype=np.float64))

    conn.constraints()

    if "power_in" in inputs:
        h.addConstrs(conn.power_in == np.asarray(inputs["power_in"], dtype=np.float64))

    objective_terms = []
    if inputs.get("minimize_cost"):
        cost = conn.cost()
        assert cost is not None
        objective_terms.append(cost)

    maximize = inputs.get("maximize", {})
    for name, weight in maximize.items():
        flow = getattr(conn, name)
        objective_terms.append(-float(weight) * Highs.qsum(flow))

    if objective_terms:
        h.minimize(Highs.qsum(objective_terms))
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
        outputs[key] = tuple(float(v) for v in h.vals(flow))
    return outputs


@pytest.mark.parametrize("case", test_data.CONNECTION_SEGMENT_SCENARIOS, ids=lambda c: c["description"])
def test_connection_scenarios(case: ConnectionScenario) -> None:
    """Connections should match expected inputs/outputs."""
    outputs = _solve_connection_scenario(case)
    _assert_expected_outputs(outputs, case["expected_outputs"])


@pytest.mark.parametrize("case", test_data.SEGMENT_ERROR_SCENARIOS, ids=lambda c: c["description"])
def test_segment_error_scenarios(case: SegmentErrorScenario) -> None:
    """Segments should raise errors for invalid configurations."""
    h = create_solver()
    periods = np.asarray(case["periods"], dtype=np.float64)
    endpoint_factory = case.get("endpoint_factory")
    if endpoint_factory is None:
        source = DummyElement("source", periods, h)
        target = DummyElement("target", periods, h)
    else:
        source, target = endpoint_factory(h, periods)

    match = case["match"]
    pv = h.addVariables(len(periods), lb=0, name_prefix="err_", out_array=True)
    if match is None:
        with pytest.raises(case["error"]):
            case["factory"](
                "seg",
                len(periods),
                periods,
                h,
                spec=case["spec"],
                source_element=source,
                target_element=target,
                power_in=pv,
            )
    else:
        with pytest.raises(case["error"], match=match):
            case["factory"](
                "seg",
                len(periods),
                periods,
                h,
                spec=case["spec"],
                source_element=source,
                target_element=target,
                power_in=pv,
            )


def test_segment_spec_typeguards() -> None:
    """Type guard helpers identify segment specs by type."""
    assert is_efficiency_spec(
        {"segment_type": "efficiency", "efficiency_source_target": None, "efficiency_target_source": None}
    )
    assert is_passthrough_spec({"segment_type": "passthrough"})
    assert is_power_limit_spec({"segment_type": "power_limit"})
    assert is_pricing_spec({"segment_type": "pricing", "price_source_target": None, "price_target_source": None})
    assert is_soc_pricing_spec({"segment_type": "soc_pricing"})


def test_segment_outputs_and_cost_coverage() -> None:
    """Segment helpers expose outputs, costs, and period metadata."""
    h = create_solver()
    periods = np.asarray([1.0, 1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)
    power = h.addVariables(len(periods), lb=0, name_prefix="dummy_", out_array=True)
    segment = DummySegment(
        "seg", len(periods), periods, h, source_element=source, target_element=target, power_in=power
    )

    np.testing.assert_array_equal(segment.periods, periods)

    outputs = segment.outputs()
    assert "coverage_output" in outputs

    cost_value = segment.cost()
    assert cost_value is not None


def test_soc_pricing_cost_none_without_prices() -> None:
    """SOC pricing cost returns None when no prices are configured."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    stored_energy = h.addVariables(2, lb=0, name_prefix="battery_e_", out_array=True)
    battery = DummyElement("battery", periods, h)
    battery.stored_energy = stored_energy  # type: ignore[attr-defined]
    target = DummyElement("target", periods, h)
    pv = h.addVariables(len(periods), lb=0, name_prefix="soc_test_", out_array=True)
    segment = SocPricingSegment(
        "seg",
        len(periods),
        periods,
        h,
        spec={"segment_type": "soc_pricing"},
        source_element=battery,
        target_element=target,
        power_in=pv,
    )

    # Apply with dummy variables
    pv = h.addVariables(len(periods), lb=0, name_prefix="soc_test_", out_array=True)

    assert segment.cost() is None


def test_efficiency_segment_treats_none_as_unity_after_update() -> None:
    """Efficiency segment should treat None values as 100% efficiency."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)

    pts = h.addVariables(len(periods), lb=0, name_prefix="eff_ts_", out_array=True)
    segment = EfficiencySegment(
        "seg",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency", "efficiency": np.array([0.9], dtype=np.float64)},
        source_element=source,
        target_element=target,
        power_in=pts,
    )

    # Simulate coordinator update path clearing optional efficiency.
    segment.efficiency = None
    h.addConstrs(segment.power_in == np.asarray([10.0], dtype=np.float64))
    h.run()

    np.testing.assert_allclose(h.vals(segment.power_out), [10.0], rtol=1e-6, atol=1e-6)


def test_efficiency_segment_treats_missing_values_as_unity_both_directions() -> None:
    """Missing efficiency values should keep both directions lossless."""
    h = create_solver()
    periods = np.asarray([1.0], dtype=np.float64)
    source = DummyElement("source", periods, h)
    target = DummyElement("target", periods, h)
    pst = h.addVariables(len(periods), lb=0, name_prefix="eff2_st_", out_array=True)
    pts = h.addVariables(len(periods), lb=0, name_prefix="eff2_ts_", out_array=True)
    seg_st = EfficiencySegment(
        "seg_st",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency"},
        source_element=source,
        target_element=target,
        power_in=pst,
    )
    seg_ts = EfficiencySegment(
        "seg_ts",
        len(periods),
        periods,
        h,
        spec={"segment_type": "efficiency"},
        source_element=source,
        target_element=target,
        power_in=pts,
    )

    h.addConstrs(seg_st.power_in == np.asarray([7.5], dtype=np.float64))
    h.addConstrs(seg_ts.power_in == np.asarray([3.5], dtype=np.float64))
    h.run()

    np.testing.assert_allclose(h.vals(seg_st.power_out), [7.5], rtol=1e-6, atol=1e-6)
    np.testing.assert_allclose(h.vals(seg_ts.power_out), [3.5], rtol=1e-6, atol=1e-6)

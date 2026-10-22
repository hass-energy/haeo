"""Unit tests for Network class."""

import itertools
import logging
from unittest.mock import Mock

from highspy import HighsBasisStatus, HighsIis, HighsModelStatus, HighsStatus
import numpy as np
import pytest

from custom_components.haeo.core.model import Network, SolverError
from custom_components.haeo.core.model import infeasibility as infeasibility_module
from custom_components.haeo.core.model import network as network_module
from custom_components.haeo.core.model.element import Element
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_BATTERY as ELEMENT_TYPE_BATTERY
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_CONNECTION as ELEMENT_TYPE_CONNECTION
from custom_components.haeo.core.model.elements import MODEL_ELEMENT_TYPE_NODE as ELEMENT_TYPE_NODE
from custom_components.haeo.core.model.elements import ModelElementConfig
from custom_components.haeo.core.model.elements.connection import Connection, ConnectionElementConfig, tie_break_offset
from custom_components.haeo.core.model.elements.policy_pricing import ELEMENT_TYPE as ELEMENT_TYPE_POLICY_PRICING
from custom_components.haeo.core.model.elements.policy_pricing import PolicyPricingElementConfig, PolicyPricingTerm
from custom_components.haeo.core.model.elements.segments import PowerLimitSegment
from custom_components.haeo.core.model.infeasibility import InfeasibleError, RelaxedRows, RowLabel
from custom_components.haeo.core.model.linear import LinearArray
from custom_components.haeo.core.model.network import BlendWeightSearch, SolveOptions, _bisect_boundary
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.model.reactive import cost
from custom_components.haeo.core.model.solver import Solver
from custom_components.haeo.core.model.util.solver_rows import add_rows

# Test constants
HOURS_PER_DAY = 24
DEFAULT_PERIODS = 24
CONNECTION_PERIODS = 3


def test_network_initialization() -> None:
    """Test network initialization."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * HOURS_PER_DAY),
    )

    assert network.name == "test_network"
    np.testing.assert_array_equal(network.periods, [1.0] * DEFAULT_PERIODS)  # Periods in hours
    assert network.n_periods == DEFAULT_PERIODS
    assert len(network.elements) == 0


def test_network_add_duplicate_element() -> None:
    """Test adding duplicate element to network."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add first battery
    battery1 = network.add(
        {"element_type": ELEMENT_TYPE_BATTERY, "name": "test_battery", "capacity": 10000, "initial_charge": 5000}
    )  # 50% of 10000
    assert battery1 is not None

    # Try to add another element with same name
    network.add(
        {"element_type": ELEMENT_TYPE_BATTERY, "name": "test_battery", "capacity": 15000, "initial_charge": 11250}
    )  # 75% of 15000

    # Network handles duplicates
    assert "test_battery" in network.elements


def test_connect_entities() -> None:
    """Test connecting entities in the network."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add entities
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})

    # Connect them
    connection = network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "battery1_to_grid1",
            "source": "battery1",
            "target": "grid1",
            "tags": {1},
            "segments": {
                "power_limit": {
                    "segment_type": "power_limit",
                    "max_power": 5000.0,
                }
            },
        }
    )

    assert connection is not None
    assert connection.name == "battery1_to_grid1"
    assert connection.source == "battery1"
    assert connection.target == "grid1"
    assert connection.power_in is not None
    assert connection.power_out is not None
    assert len(connection.total_power_in) == CONNECTION_PERIODS
    assert len(connection.total_power_out) == CONNECTION_PERIODS
    # Check that the connection element was added
    connection_name = "battery1_to_grid1"
    assert connection_name in network.elements
    assert isinstance(network.elements[connection_name], Connection)


def test_connect_nonexistent_entities() -> None:
    """Test connecting nonexistent entities."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    with pytest.raises(ValueError, match="Source element 'nonexistent' is not a network participant"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "nonexistent",
                "target": "also_nonexistent",
                "tags": {1},
            }
        )


def test_connect_nonexistent_target_entity() -> None:
    """Test connecting to nonexistent target entity."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add only source entity
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    # Try to connect to nonexistent target
    with pytest.raises(ValueError, match="Target element 'nonexistent' is not a network participant"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "battery1",
                "target": "nonexistent",
                "tags": {1},
            }
        )


def test_connect_source_is_connection() -> None:
    """Test connecting when source is a connection element."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add entities and a connection
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})
    network.add(
        {"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn1", "source": "battery1", "target": "grid1", "tags": {1}}
    )

    # Try to create another connection using the connection as source
    with pytest.raises(ValueError, match="Source element 'conn1' is not a network participant"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "conn1",
                "target": "battery1",
                "tags": {1},
            }
        )


def test_connect_target_is_connection() -> None:
    """Test connecting when target is a connection element."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )
    # Add entities and a connection
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery1", "capacity": 10000, "initial_charge": 5000})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid1", "is_sink": False, "is_source": True})
    network.add(
        {"element_type": ELEMENT_TYPE_CONNECTION, "name": "conn1", "source": "battery1", "target": "grid1", "tags": {1}}
    )

    # Try to create another connection using the connection as target
    with pytest.raises(ValueError, match="Target element 'conn1' is not a network participant"):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": "bad_connection",
                "source": "battery1",
                "target": "conn1",
                "tags": {1},
            }
        )


def test_constraints_returns_empty_when_no_elements() -> None:
    """Constraints should return empty dict when network has no elements."""
    net = Network(name="net", periods=np.array([1.0]))

    assert net.constraints() == {}


def test_network_constraint_generation_error() -> None:
    """Test that constraint generation errors are caught and wrapped with context."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add a regular battery
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10000, "initial_charge": 5000})

    # Mock an element to raise an exception during constraints
    mock_element = Mock(spec=Element)
    mock_element.name = "failing_element"
    mock_element.build = Mock()
    mock_element.power_balance_constraints = {}
    mock_element.power_consumption = None
    mock_element.power_production = None
    mock_element.cost = Mock(return_value=None)
    mock_element.constraints.side_effect = RuntimeError("Constraint generation failed")
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to apply constraints for element 'failing_element'"):
        network.optimize()


def test_network_optimize_constraints_error() -> None:
    """Test that optimize() catches and wraps constraints errors."""
    network = Network(
        name="test_network",
        periods=np.array([1.0] * 3),
    )

    # Add a regular element
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node1", "is_sink": True, "is_source": True})

    # Mock an element that raises an exception during constraints
    mock_element = Mock(spec=Element)
    mock_element.constraints.side_effect = RuntimeError("Build failed")
    mock_element.cost = Mock(return_value=None)
    network.elements["failing_element"] = mock_element

    # Should wrap the error with context about which element failed
    with pytest.raises(ValueError, match="Failed to apply constraints for element 'failing_element'"):
        network.optimize()


def test_network_optimize_success_logs_solver_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Optimize should return the objective and log solver streams."""

    caplog.set_level(logging.DEBUG, logger=network_module.__name__)

    network = Network(name="test_network", periods=np.array([1.0] * 2))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "src", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "dst", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "src",
            "target": "dst",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": 0.0}},
        }
    )

    result = network.optimize()

    assert result == 0.0


def test_log_callback_handles_empty_message() -> None:
    """Test _log_callback handles empty messages gracefully."""
    # Should not raise, just verify it doesn't crash
    Network._log_callback(0, "")
    Network._log_callback(1, "   ")  # Whitespace only


def test_network_optimize_raises_when_the_solver_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A solve that fails for any reason but infeasibility raises once every blend weight has failed too."""
    # Create a network with objectives (needs connections for secondary)
    network = Network(name="test_network", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "src", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "dst", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": "connection",
            "name": "conn",
            "source": "src",
            "target": "dst",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": 0.10}},
        }
    )

    # Track if run() has been called
    run_called = False

    original_run = network._solver.run
    original_get_model_status = network._solver.getModelStatus

    def mock_run() -> None:
        nonlocal run_called
        original_run()
        run_called = True

    def mock_get_model_status() -> HighsModelStatus:
        # After run() is called, return a non-optimal status
        if run_called:
            return HighsModelStatus.kSolveError
        return original_get_model_status()

    monkeypatch.setattr(network._solver, "run", mock_run)
    monkeypatch.setattr(network._solver, "getModelStatus", mock_get_model_status)

    with pytest.raises(SolverError) as error:
        network.optimize()
    assert error.value.status == "Solve error"


def _over_demanded_network(*, relax_infeasible: bool = False) -> Network:
    """Return a network whose fixed load needs more than the grid and battery can give in its middle period."""
    network = Network(name="test", periods=np.array([1.0, 1.0, 1.0]), relax_infeasible=relax_infeasible)
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "switchboard", "is_source": False, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10.0, "initial_charge": 10.0})
    connections: list[ConnectionElementConfig] = [
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "grid:import",
            "source": "grid",
            "target": "switchboard",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": 10.0},
                "pricing": {"segment_type": "pricing", "price": 0.30},
            },
        },
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "battery:discharge",
            "source": "battery",
            "target": "switchboard",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
        },
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "load:connection",
            "source": "switchboard",
            "target": "load",
            "tags": {1},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([3.0, 15.5, 3.0]), "fixed": True}
            },
        },
    ]
    for connection in connections:
        network.add(connection)
    return network


def test_infeasible_network_names_the_conflicting_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    """An infeasible network raises at once, naming the smallest set of constraints that conflict."""
    network = _over_demanded_network()
    solver = network._solver
    runs = 0
    real_run = solver.run

    def counted_run() -> HighsStatus:
        nonlocal runs
        runs += 1
        return real_run()

    monkeypatch.setattr(solver, "run", counted_run)

    with pytest.raises(InfeasibleError) as error:
        network.optimize()

    assert set(error.value.conflicts) == {
        RowLabel("switchboard", "element_power_balance", 1, balance=True),
        RowLabel("grid:import", "power_limit_power_limit", 1),
        RowLabel("battery:discharge", "power_limit_power_limit", 1),
        RowLabel("load:connection", "power_limit_power_limit", 1),
    }
    assert "switchboard element_power_balance[1]" in str(error.value)
    # One blended solve, confirmed infeasible for the cost alone, and no other blend weight tried
    assert runs == 2


def test_relaxed_network_leaves_the_shortfall_at_a_power_balance() -> None:
    """A relaxed plan meets the load and leaves the energy no source could supply at the switchboard."""
    network = _over_demanded_network(relax_infeasible=True)

    network.optimize()

    shortfall = RowLabel("switchboard", "element_power_balance", 1, balance=True)
    [relaxation] = network.relaxations
    assert relaxation.row == shortfall
    assert relaxation.amount == pytest.approx(-0.5)
    assert shortfall in network.conflicts
    load_power = network.elements["load:connection"].outputs()["connection_power"]
    assert isinstance(load_power, OutputData)
    np.testing.assert_allclose(load_power.values, [3.0, 15.5, 3.0], atol=1e-9)
    # The relaxed balance is back to holding exactly once the plan is found
    balance_row = int(network.constraints()["switchboard"]["element_power_balance"][1])
    lp = network._solver.getLp()
    assert (lp.row_lower_[balance_row], lp.row_upper_[balance_row]) == (0.0, 0.0)


def test_relaxations_report_what_the_delivered_plan_does(monkeypatch: pytest.MonkeyPatch) -> None:
    """A row widened further than the delivered plan uses is reported by how far the plan takes it, not the widening.

    The relaxation also lets the switchboard dump 1 kWh in the first period, which
    the plan has no reason to do, since that energy would cost money to import.
    """
    network = _over_demanded_network(relax_infeasible=True)
    real_relaxed_rows = infeasibility_module.relaxed_rows
    surplus = RowLabel("switchboard", "element_power_balance", 0, balance=True)

    def widened_relaxed_rows(solver: Solver, labels: dict[int, RowLabel]) -> RelaxedRows | None:
        relaxed = real_relaxed_rows(solver, labels)
        assert relaxed is not None
        [row] = [row for row, label in labels.items() if label == surplus]
        return RelaxedRows(
            np.append(relaxed.rows, np.int32(row)),
            np.append(relaxed.values, 1.0),
            np.append(relaxed.lower, 0.0),
            np.append(relaxed.upper, 0.0),
        )

    monkeypatch.setattr(infeasibility_module, "relaxed_rows", widened_relaxed_rows)

    network.optimize()

    assert [relaxation.row for relaxation in network.relaxations] == [
        RowLabel("switchboard", "element_power_balance", 1, balance=True)
    ]
    assert network.relaxations[0].amount == pytest.approx(-0.5)


def test_relaxations_clear_once_the_network_is_feasible_again() -> None:
    """A later solve the network can meet in full reports no relaxations."""
    network = _over_demanded_network(relax_infeasible=True)
    network.optimize()

    load_limit = network.elements["load:connection"]["power_limit"]
    assert isinstance(load_limit, PowerLimitSegment)
    load_limit.max_power = np.array([3.0, 12.0, 3.0])
    network.optimize()

    assert network.relaxations == ()
    assert network.conflicts == ()


def test_infeasible_network_is_recognised_when_presolve_cannot_say_whether_it_is_unbounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A model presolve reports as unbounded or infeasible is solved again without presolve to learn which."""
    network = _over_demanded_network()
    solver = network._solver
    real_status = solver.getModelStatus
    statuses = iter([HighsModelStatus.kUnboundedOrInfeasible])
    monkeypatch.setattr(solver, "getModelStatus", lambda: next(statuses, None) or real_status())

    with pytest.raises(InfeasibleError) as error:
        network.optimize()

    assert error.value.conflicts
    assert solver.getOptionValue("presolve") == (HighsStatus.kOk, "choose")


def test_blend_reported_infeasible_is_solved_when_the_cost_alone_is_feasible(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blended solve wrongly reported infeasible lowers the weight instead of failing the plan."""
    network = _over_demanded_network()
    load_limit = network.elements["load:connection"]["power_limit"]
    assert isinstance(load_limit, PowerLimitSegment)
    load_limit.max_power = np.array([3.0, 12.0, 3.0])
    solver = network._solver
    real_status = solver.getModelStatus
    statuses = iter([HighsModelStatus.kInfeasible])
    monkeypatch.setattr(solver, "getModelStatus", lambda: next(statuses, None) or real_status())

    network.optimize()

    assert network.conflicts == ()


def test_relaxed_plan_the_solver_still_finds_infeasible_raises_with_the_conflicts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A re-solve that stays infeasible after relaxing reports the conflicts already found."""
    network = _over_demanded_network(relax_infeasible=True)
    empty = np.zeros(0)
    monkeypatch.setattr(
        infeasibility_module,
        "relaxed_rows",
        lambda *_args: RelaxedRows(np.zeros(0, dtype=np.int32), empty, empty, empty),
    )

    with pytest.raises(InfeasibleError) as error:
        network.optimize()

    assert error.value.conflicts
    assert error.value.conflicts == network.conflicts


def test_infeasible_network_reports_no_conflicts_when_the_solver_finds_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """When HiGHS cannot name a conflicting subsystem the error still reports the infeasibility."""
    network = _over_demanded_network()
    monkeypatch.setattr(network._solver, "getIis", lambda: (HighsStatus.kError, HighsIis()))

    with pytest.raises(InfeasibleError) as error:
        network.optimize()

    assert error.value.conflicts == ()
    assert str(error.value) == "Optimization failed with status: Infeasible"


def test_relaxation_the_solver_cannot_find_raises_with_the_conflicts(monkeypatch: pytest.MonkeyPatch) -> None:
    """When HiGHS cannot relax the rows, the relaxed network raises like any other infeasible one."""
    network = _over_demanded_network(relax_infeasible=True)
    monkeypatch.setattr(network._solver, "feasibilityRelaxation", lambda *_args: HighsStatus.kError)

    with pytest.raises(InfeasibleError) as error:
        network.optimize()

    assert error.value.conflicts


def test_network_cost_with_multiple_elements() -> None:
    """Test Network.cost() aggregates costs from multiple elements."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))

    # Add two nodes
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "target", "is_source": False, "is_sink": True})

    # Add two connections with pricing (each creates costs)
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn1",
            "source": "source",
            "target": "target",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([10.0, 20.0])},
            },
        }
    )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn2",
            "source": "target",
            "tags": {1},
            "target": "source",
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([5.0, 10.0])},
            },
        }
    )

    primary, secondary = network.cost()

    assert primary is not None
    assert secondary is not None


def test_network_cost_is_empty_when_no_costs() -> None:
    """Network.cost() has neither a primary nor a secondary cost when no element has one."""
    network = Network(name="test", periods=np.array([1.0]))

    # Add a node (has no costs)
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "node", "is_source": True, "is_sink": True})

    assert network.cost() == (None, None)


def test_network_constraints_empty_when_no_elements() -> None:
    """Test Network.constraints() returns empty dict with no elements."""
    network = Network(name="test", periods=np.array([1.0]))

    # No elements added - should return empty dict
    constraints = network.constraints()
    assert constraints == {}


# ---------------------------------------------------------------------------
# Helpers for multi-objective tests
# ---------------------------------------------------------------------------


def _build_priced_network(options: SolveOptions | None = None) -> Network:
    """Build a small network with primary (cost) and secondary (time pref) objectives.

    Topology: source --[conn]--> sink
    The connection has pricing so it generates a primary cost objective,
    and the bidirectional flow gives the solver a nontrivial decision.
    """
    network = Network(name="test", periods=np.array([1.0, 1.0]), options=options)

    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "sink",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([10.0, 20.0])},
            },
        }
    )
    return network


# ---------------------------------------------------------------------------
# SolveOptions tests
# ---------------------------------------------------------------------------


def test_solve_options_defaults() -> None:
    """SolveOptions default values match HiGHS defaults."""
    opts = SolveOptions()
    assert opts.simplex_strategy == 4


def test_solve_options_apply() -> None:
    """SolveOptions.apply() sets all HiGHS options on the solver."""
    opts = SolveOptions(simplex_strategy=4, presolve="on")
    h = Solver()
    h.setOptionValue("output_flag", False)
    opts.apply(h)
    assert h.getOptionValue("simplex_strategy")[1] == 4
    assert h.getOptionValue("presolve")[1] == "on"


def test_solve_options_propagated_to_network() -> None:
    """Network.__post_init__ applies SolveOptions to the solver."""
    opts = SolveOptions(simplex_strategy=4)
    network = Network(name="test", periods=np.array([1.0]), options=opts)
    assert network._solver.getOptionValue("simplex_strategy")[1] == 4


# ---------------------------------------------------------------------------
# Blend weight tests
# ---------------------------------------------------------------------------


def test_first_call_calibrates_the_weight() -> None:
    """The first call calibrates the starting weight."""
    network = _build_priced_network()
    assert network._blend_weight is None
    network.optimize()
    assert network._blend_weight is not None
    assert network._blend_weight > 0


def test_subsequent_calls_reuse_the_weight() -> None:
    """After calibration, optimize() solves the blend with the calibrated weight."""
    network = _build_priced_network()
    r1 = network.optimize()  # calibrate
    r2 = network.optimize()  # blended with calibrated weight
    assert r1 == pytest.approx(r2)


def test_solves_with_negligible_objective_coefficients() -> None:
    """A primary objective term below HiGHS's small matrix value solves, and solves again (#501)."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "sink",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([10.0, 3e-10])},
            },
        }
    )

    first = network.optimize()
    second = network.optimize()

    assert np.isfinite(first)
    assert second == pytest.approx(first)


def test_optimize_raises_no_primary_cost() -> None:
    """Network with secondary but no primary cost raises ValueError."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "src", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "dst", "is_source": False, "is_sink": True})
    # Connection without pricing — has secondary (time preference) but no primary
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "src",
            "target": "dst",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": 5.0}},
        }
    )
    with pytest.raises(ValueError, match="no primary cost"):
        network.optimize()


def test_optimize_raises_no_secondary_cost() -> None:
    """A network with a cost but no connections has no secondary cost."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_BATTERY, "name": "battery", "capacity": 10.0, "initial_charge": 5.0})
    with pytest.raises(ValueError, match="no secondary cost"):
        network.optimize()


def test_bisect_boundary_converges() -> None:
    """_bisect_boundary finds the transition point."""
    result = _bisect_boundary(0.0, 10.0, lambda x: x < 5.0, max_steps=50, convergence=0.01)
    assert abs(result - 5.0) < 0.02


def test_bisect_boundary_respects_max_steps() -> None:
    """_bisect_boundary stops at max_steps."""
    calls = [0]

    def pred(x: float) -> bool:
        calls[0] += 1
        return x < 5.0

    _bisect_boundary(0.0, 10.0, pred, max_steps=3, convergence=0.001)
    assert calls[0] == 3


def test_calibrated_mode_zero_primary_cost_vector() -> None:
    """Calibration returns safe default when primary cost vector is all zeros."""
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "source", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "sink", "is_source": False, "is_sink": True})
    # Pricing with all-zero prices: primary cost vector exists but is all zeros.
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "source",
            "target": "sink",
            "tags": {1},
            "segments": {
                "pricing": {"segment_type": "pricing", "price": np.array([0.0, 0.0])},
            },
        }
    )
    result = network.optimize()
    assert np.isfinite(result)
    assert network._blend_weight == pytest.approx(10.0 ** (network_module._CAL_LOG_HI - network_module._CAL_MARGIN))


def test_policy_pricing_charges_the_measured_power() -> None:
    """A policy price on a connection is charged on the power at its power limit, after efficiency losses.

    The connection loses half its power before the limit, the way a battery's discharge
    connection does, and delivering power earns 1 per kWh. With a limit of 5 the optimizer
    draws 10 and delivers 5, so a policy price of 0.1 adds 0.1 x 5, not 0.1 x 10.
    """
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "store", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "bus", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "discharge",
            "source": "store",
            "target": "bus",
            "tags": {0},
            "segments": {
                "efficiency": {"segment_type": "efficiency", "efficiency": np.array([0.5])},
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([5.0])},
                "pricing": {"segment_type": "pricing", "price": np.array([-1.0])},
            },
        }
    )
    network.add(
        PolicyPricingElementConfig(
            element_type=ELEMENT_TYPE_POLICY_PRICING,
            name="discharge_cost",
            price=0.1,
            terms=[PolicyPricingTerm(connection="discharge", tag=0)],
        )
    )

    assert network.optimize() == pytest.approx(-5.0 + 0.1 * 5.0)


def test_add_policy_pricing_unknown_connection() -> None:
    """Adding PolicyPricing referencing a missing connection raises TypeError."""
    network = Network(name="test", periods=np.array([1.0]))
    with pytest.raises(TypeError, match="references unknown connection"):
        network.add(
            PolicyPricingElementConfig(
                element_type=ELEMENT_TYPE_POLICY_PRICING,
                name="pp",
                price=0.05,
                terms=[PolicyPricingTerm(connection="missing", tag=0)],
            )
        )


def test_add_policy_pricing_unknown_tag() -> None:
    """Adding PolicyPricing referencing a tag not on the connection raises ValueError."""
    network = Network(name="test", periods=np.array([1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "a", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "b", "is_source": False, "is_sink": True})
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "conn",
            "source": "a",
            "target": "b",
            "tags": {0},
            "segments": {
                "power_limit": {"segment_type": "power_limit", "max_power": np.array([10.0])},
            },
        }
    )
    with pytest.raises(ValueError, match="references tag 99"):
        network.add(
            PolicyPricingElementConfig(
                element_type=ELEMENT_TYPE_POLICY_PRICING,
                name="pp",
                price=0.05,
                terms=[PolicyPricingTerm(connection="conn", tag=99)],
            )
        )


def _interchangeable_batteries() -> list[ModelElementConfig]:
    """Return a network where two identical batteries can cover the same load in many equally cheap ways."""
    n = 6
    elements: list[ModelElementConfig] = [
        {"element_type": ELEMENT_TYPE_NODE, "name": "grid", "is_source": True, "is_sink": False},
        {"element_type": ELEMENT_TYPE_NODE, "name": "hub", "is_source": False, "is_sink": False},
        {"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True},
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "grid_import",
            "source": "grid",
            "target": "hub",
            "tags": {1},
            "segments": {"pricing": {"segment_type": "pricing", "price": np.array([0.1, 0.1, 0.5, 0.5, 0.5, 0.5])}},
        },
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "load_supply",
            "source": "hub",
            "target": "load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.full(n, 2.0), "fixed": True}},
        },
    ]
    for battery in ("b1", "b2"):
        elements.append(
            {"element_type": ELEMENT_TYPE_BATTERY, "name": battery, "capacity": 10.0, "initial_charge": 5.0}
        )
        elements.append(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": f"{battery}_discharge",
                "source": battery,
                "target": "hub",
                "tags": {1},
                "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.full(n, 3.0)}},
            }
        )
    return elements


def test_equally_cheap_plans_do_not_depend_on_element_order() -> None:
    """Swapping energy between two batteries across periods is cost-free, yet the chosen plan is always the same.

    Without a tie-break that separates such swaps, the plan followed the order of
    the solver's rows, so adding the same elements in another order changed it.
    """
    elements = _interchangeable_batteries()
    plans: set[tuple[float, ...]] = set()
    for order in itertools.islice(itertools.permutations(range(len(elements))), 0, 720, 120):
        network = Network(name="ties", periods=np.ones(6))
        ordered = [elements[i] for i in order]
        for element in sorted(ordered, key=lambda element: element["element_type"] == ELEMENT_TYPE_CONNECTION):
            network.add(element)
        network.optimize()
        plans.add(
            tuple(
                round(value, 6)
                for battery in ("b1", "b2")
                for value in network.elements[f"{battery}_discharge"].outputs()["connection_power"].values
            )
        )

    assert len(plans) == 1


def test_tie_break_offset_is_distinct_per_connection_and_period() -> None:
    """Every connection and period of a network gets its own offset in [0, 1)."""
    values = np.concatenate([tie_break_offset(priority, 10) for priority in range(5)])

    assert np.all((values >= 0.0) & (values < 1.0))
    assert len(np.unique(values)) == len(values)


def test_blended_solve_lowers_a_weight_that_trades_away_cost() -> None:
    """A blend weight large enough to let the secondary override cost is lowered until the plan is cost-optimal.

    The secondary prefers source "a" by sort order, but "b" is cheaper, so an
    oversized weight would supply the load from "a".
    """
    network = Network(name="test", periods=np.array([1.0, 1.0]))
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "a", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "b", "is_source": True, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "hub", "is_source": False, "is_sink": False})
    network.add({"element_type": ELEMENT_TYPE_NODE, "name": "load", "is_source": False, "is_sink": True})
    for source, price in (("a", 0.30), ("b", 0.10)):
        network.add(
            {
                "element_type": ELEMENT_TYPE_CONNECTION,
                "name": f"{source}_supply",
                "source": source,
                "target": "hub",
                "tags": {1},
                "segments": {"pricing": {"segment_type": "pricing", "price": np.full(2, price)}},
            }
        )
    network.add(
        {
            "element_type": ELEMENT_TYPE_CONNECTION,
            "name": "demand",
            "source": "hub",
            "target": "load",
            "tags": {1},
            "segments": {"power_limit": {"segment_type": "power_limit", "max_power": np.full(2, 1.0), "fixed": True}},
        }
    )
    network.optimize()
    network._blend_weight = 50.0

    cost = network.optimize()

    assert cost == pytest.approx(0.2)
    assert network.elements["b_supply"].outputs()["connection_power"].values == pytest.approx((1.0, 1.0))
    assert network._blend_weight < 50.0


def _battery_plans(network: Network) -> tuple[float, ...]:
    """Return both batteries' discharge power over the horizon."""
    return tuple(
        round(value, 6)
        for battery in ("b1", "b2")
        for value in network.elements[f"{battery}_discharge"].outputs()["connection_power"].values
    )


def _network_with(elements: list[ModelElementConfig]) -> Network:
    network = Network(name="ties", periods=np.ones(6))
    for element in sorted(elements, key=lambda element: element["element_type"] == ELEMENT_TYPE_CONNECTION):
        network.add(element)
    return network


def _objectives(network: Network) -> tuple[LinearArray, LinearArray]:
    """Return the network's cost and secondary objectives."""
    primary, secondary = network.cost()
    assert primary is not None
    assert secondary is not None
    return primary, secondary


def _lexicographic_reference(elements: list[ModelElementConfig]) -> tuple[float, tuple[float, ...]]:
    """Return the cost and battery plans of the exact lexicographic optimum.

    The cost is minimized first, then the secondary with the cost bounded to its
    optimum, on a network built from the same elements.
    """
    network = _network_with(elements)
    network.optimize()
    h = network._solver
    primary, secondary = _objectives(network)
    cols = np.arange(h.numVariables, dtype=np.int32)
    h.changeColsCost(len(cols), cols, primary.column_coefficients(len(cols)))
    h.run()
    cost = h.getObjectiveValue()
    add_rows(h, primary <= cost + 1e-9 * max(1.0, abs(cost)))
    h.changeColsCost(len(cols), cols, secondary.column_coefficients(len(cols)))
    h.run()
    assert h.getModelStatus() == HighsModelStatus.kOptimal
    return cost, _battery_plans(network)


def test_blended_solve_raises_a_weight_too_small_to_break_ties() -> None:
    """A weight too small for the secondary to register is raised until the plan is in order."""
    _, expected = _lexicographic_reference(_interchangeable_batteries())
    network = _network_with(_interchangeable_batteries())
    network.optimize()
    # Start the next solve cold, from a weight far too small for the secondary
    network._solver.clearSolver()
    network._blend_weight = 1e-11

    network.optimize()

    assert _battery_plans(network) == expected
    assert network._blend_weight > 1e-11


def test_weight_search_lowers_the_weight_while_the_plan_is_not_cost_optimal() -> None:
    """Without a known cost-optimal weight, the weight is lowered by a step."""
    search = BlendWeightSearch()

    assert search.next_weight(1e-3, cost_optimal=False, order_optimal=True) == pytest.approx(
        1e-3 / network_module._WEIGHT_STEP
    )


def test_weight_search_stops_lowering_at_the_smallest_weight() -> None:
    """The weight is not lowered below the smallest weight tried."""
    search = BlendWeightSearch()

    assert search.next_weight(1e-12, cost_optimal=False, order_optimal=True) is None


def test_weight_search_raises_an_out_of_order_weight() -> None:
    """A cost-optimal plan out of order raises the weight by a step while no weight is known too large."""
    search = BlendWeightSearch()

    assert search.next_weight(1e-6, cost_optimal=True, order_optimal=False) == pytest.approx(
        1e-6 * network_module._WEIGHT_STEP
    )
    assert search.next_weight(5e-4, cost_optimal=True, order_optimal=False) == pytest.approx(
        5e-4 * network_module._WEIGHT_STEP
    )


def test_weight_search_never_raises_to_a_weight_too_large_for_the_cost() -> None:
    """Once a weight is known too large for the cost, raising bisects below it."""
    search = BlendWeightSearch()
    search.next_weight(1e-4, cost_optimal=False, order_optimal=True)

    raised = search.next_weight(1e-6, cost_optimal=True, order_optimal=False)

    assert raised == pytest.approx(1e-5)
    assert raised is not None
    assert raised < 1e-4


def test_weight_search_keeps_the_cost_optimal_plan_when_no_gap_is_left() -> None:
    """A cost-optimal plan out of order is kept when no weight is left below one too large for the cost."""
    search = BlendWeightSearch()
    search.next_weight(1.5e-6, cost_optimal=False, order_optimal=True)

    assert search.next_weight(1e-6, cost_optimal=True, order_optimal=False) is None


def test_weight_search_settles_on_the_cost_optimal_weight_when_no_gap_is_left() -> None:
    """When a raise fails the cost and no gap is left, the search returns to the cost-optimal weight."""
    search = BlendWeightSearch()
    search.next_weight(1e-6, cost_optimal=True, order_optimal=False)

    assert search.next_weight(1.5e-6, cost_optimal=False, order_optimal=True) == pytest.approx(1e-6)


def test_weight_search_lowers_again_when_a_known_cost_optimal_weight_fails_the_cost() -> None:
    """A weight that passed the cost earlier but fails it now is no longer treated as cost-optimal."""
    search = BlendWeightSearch()
    search.next_weight(1e-6, cost_optimal=True, order_optimal=False)
    assert search.next_weight(1.5e-6, cost_optimal=False, order_optimal=True) == pytest.approx(1e-6)

    assert search.next_weight(1e-6, cost_optimal=False, order_optimal=True) == pytest.approx(
        1e-6 / network_module._WEIGHT_STEP
    )


def test_weight_search_stops_raising_at_the_largest_weight() -> None:
    """The weight is not raised above the largest weight tried."""
    search = BlendWeightSearch()

    assert search.next_weight(1e-1, cost_optimal=True, order_optimal=False) is None


def test_blended_solve_falls_back_to_the_cost_when_no_weight_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """When every weight fails the cost check, the plan is the cheapest one and the previous weight is kept."""
    expected, _ = _lexicographic_reference(_interchangeable_batteries())
    network = _network_with(_interchangeable_batteries())
    network.optimize()
    weight = network._blend_weight
    monkeypatch.setattr(Network, "_solve_at", lambda *_args: (0.0, False, True))

    cost = network.optimize()

    assert cost == pytest.approx(expected)
    assert network._solver.getModelStatus() == HighsModelStatus.kOptimal
    assert network._blend_weight == weight


class _FixedCharge(Element[str]):
    """An element whose only cost is a fixed charge that no plan can change."""

    @cost
    def fixed_charge(self) -> LinearArray:
        """Charge the same amount whatever the plan."""
        return LinearArray.constants(2.5)


@pytest.mark.parametrize("cost_alone", [False, True], ids=["blended", "cost_alone"])
def test_a_constant_cost_is_part_of_the_plan_cost(monkeypatch: pytest.MonkeyPatch, *, cost_alone: bool) -> None:
    """A cost that does not depend on the plan still counts toward the cost the network reports."""
    network = _network_with(_interchangeable_batteries())
    base = network.optimize()
    network.elements["fixed"] = _FixedCharge("fixed", network.periods, solver=network._solver, output_names=frozenset())
    if cost_alone:
        monkeypatch.setattr(Network, "_solve_at", lambda *_args: (0.0, False, True))

    assert network.optimize() == pytest.approx(base + 2.5)


def test_a_failed_solve_counts_against_the_weight(monkeypatch: pytest.MonkeyPatch) -> None:
    """A blended solve that does not reach an optimum is treated as not cost-optimal, so the weight is lowered."""
    network = _network_with(_interchangeable_batteries())
    network.optimize()
    h = network._solver
    objectives = network_module.Objectives.of(*_objectives(network), h.numVariables)
    monkeypatch.setattr(h, "getModelStatus", lambda: HighsModelStatus.kUnknown)

    _, cost_optimal, _ = network._solve_at(np.arange(h.numVariables, dtype=np.int32), objectives, 1e-6)

    assert not cost_optimal


def test_weight_search_keeps_a_cost_optimal_plan_in_order() -> None:
    """A plan that passes both checks is kept."""
    search = BlendWeightSearch()

    assert search.next_weight(1e-4, cost_optimal=True, order_optimal=True) is None


def test_checking_a_plan_leaves_it_and_its_basis_unchanged() -> None:
    """Checking a plan prices at its basis with no iterations, keeping the plan and its basic variables."""
    network = _network_with(_interchangeable_batteries())
    network.optimize()
    h = network._solver
    plan = np.asarray(h.getSolution().col_value).copy()
    basis = h.getBasis()
    basic = [status == HighsBasisStatus.kBasic for status in [*basis.col_status, *basis.row_status]]
    cols = np.arange(h.getNumCol(), dtype=np.int32)
    weight = network._blend_weight
    assert weight is not None
    blended = network_module.Objectives.of(*_objectives(network), len(cols)).blend(weight)
    # Same blend as the plan was solved with, so its solve stays put, but a cost of all ones to price
    ones = network_module.Objective(np.ones(len(cols)), 0.0)
    secondary = network_module.Objective((blended.costs - ones.costs) / weight, blended.offset / weight)

    network._solve_at(cols, network_module.Objectives(ones, secondary), weight)

    after = h.getBasis()
    assert h.getInfo().simplex_iteration_count == 0
    np.testing.assert_array_equal(np.asarray(h.getSolution().col_value), plan)
    assert [status == HighsBasisStatus.kBasic for status in [*after.col_status, *after.row_status]] == basic

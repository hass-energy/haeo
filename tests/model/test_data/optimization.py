"""Optimization utilities for element scenario testing.

This module provides helper functions for creating minimal optimization problems
to test individual elements with complementary power sources/sinks.
"""

from collections.abc import Sequence
from typing import Any

from pulp import LpMinimize, LpProblem, LpVariable, getSolver, lpSum
from pulp import value as lp_value

from custom_components.haeo.model.connection import Connection
from custom_components.haeo.model.grid import Grid


def create_power_variables(
    values: Sequence[float | None], name: str = "power", cost: float = 0.0
) -> tuple[list[LpVariable | float], float]:
    """Create power variables from a sequence of values.

    Args:
        values: Power values for each period. None = unbounded variable, float = fixed value
        name: Base name for variables
        cost: Cost per kWh (positive = cost to consume, negative = revenue for consuming)

    Returns:
        Tuple of (power_variables, cost_per_kwh)

    """
    power_vars: list[LpVariable | float] = []
    for i, val in enumerate(values):
        if val is None:
            # Unbounded variable (infinite source/sink)
            power_vars.append(LpVariable(name=f"{name}_{i}", lowBound=None, upBound=None))
        else:
            # Fixed value
            power_vars.append(float(val))
    return power_vars, cost


def extract_solution(variable: LpVariable | float | None) -> float:
    """Extract the solved value from an LP variable or return the float value.

    Args:
        variable: LP variable or float value

    Returns:
        The numeric value

    """
    if variable is None:
        return 0.0
    if isinstance(variable, (int, float)):
        return float(variable)
    return float(lp_value(variable))  # type: ignore[no-untyped-call]


def extract_solution_sequence(variables: Sequence[LpVariable | float] | None) -> tuple[float, ...]:
    """Extract solved values from a sequence of LP variables.

    Args:
        variables: Sequence of LP variables or float values

    Returns:
        Tuple of numeric values

    """
    if variables is None:
        return ()
    return tuple(extract_solution(v) for v in variables)


def solve_problem(problem: LpProblem, silent: bool = True) -> Any:
    """Solve an optimization problem.

    Args:
        problem: PuLP problem to solve
        silent: Whether to suppress solver output (default True)

    Returns:
        Status code (1 = optimal, other = failed)

    """
    solver = getSolver("HiGHS", msg=0 if silent else 1)
    return problem.solve(solver)  # type: ignore[no-untyped-call]


def calculate_power_cost(power_vars: Sequence[LpVariable | float], cost_per_kwh: float, period: float) -> Any:
    """Calculate total cost for power variables.

    Args:
        power_vars: Power variables or fixed values
        cost_per_kwh: Cost per kWh
        period: Time period in hours

    Returns:
        Total cost expression or value

    """
    if cost_per_kwh == 0.0:
        return 0.0
    return lpSum(power_vars[i] * cost_per_kwh * period for i in range(len(power_vars)))


def solve_element_scenario(element: Any, inputs: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Solve an optimization scenario for an element and return outputs.

    Args:
        element: The element to test (Battery, Grid, Photovoltaics, etc.)
        inputs: Input configuration with 'power' or 'source_power'/'target_power' as sequences
                where None = unbounded variable, float = fixed value

    Returns:
        Dict mapping output names to output data dicts with type, unit, and values

    """
    # Get n_periods and period based on element type
    if isinstance(element, Connection):
        n_periods = len(element.power_source_target)
        period = element.period
    else:
        n_periods = element.n_periods
        period = element.period

    # Create complementary power variables based on element type
    if isinstance(element, Connection):
        # Connections need source and target power inputs
        source_power = inputs.get("source_power", [None] * n_periods)
        target_power = inputs.get("target_power", [None] * n_periods)
        source_cost = inputs.get("source_cost", 0.0)
        target_cost = inputs.get("target_cost", 0.0)

        source_vars, _ = create_power_variables(source_power, "source_power", source_cost)
        target_vars, _ = create_power_variables(target_power, "target_power", target_cost)

        # Build optimization problem
        problem = LpProblem(f"test_{element.name}", LpMinimize)  # type: ignore[no-untyped-call]

        # Add element constraints
        for constraint in element.constraints():
            problem += constraint

        # Add power balance constraints for connections
        # Net power at source = power_source_target - power_target_source
        # Net power at target = power_target_source - power_source_target (inverted)
        for i in range(n_periods):
            # Source side: net flow out = forward - reverse
            problem += source_vars[i] == element.power_source_target[i] - element.power_target_source[i]
            # Target side: net flow in = forward - reverse (opposite perspective)
            problem += target_vars[i] == element.power_source_target[i] - element.power_target_source[i]

        # Set objective
        total_cost = element.cost()
        total_cost += calculate_power_cost(source_vars, source_cost, period)
        total_cost += calculate_power_cost(target_vars, target_cost, period)
        problem += total_cost

    else:
        # Regular elements (Battery, Grid, PV, Load, Node)
        power = inputs.get("power", [None] * n_periods)
        power_cost = inputs.get("cost", 0.0)

        power_vars, _ = create_power_variables(power, "power", power_cost)

        # Build optimization problem
        problem = LpProblem(f"test_{element.name}", LpMinimize)  # type: ignore[no-untyped-call]

        # Add element constraints
        for constraint in element.constraints():
            problem += constraint

        # Add power balance constraints
        # Convention: Positive power_vars = power FROM external TO element
        #             Negative power_vars = power FROM element TO external
        has_consumption = hasattr(element, "power_consumption") and element.power_consumption is not None
        has_production = hasattr(element, "power_production") and element.power_production is not None
        is_grid = isinstance(element, Grid)

        if has_consumption and has_production:
            # Elements with both (Battery, Grid)
            if is_grid:
                # Grid: consumption=export, production=import
                # power_vars > 0 means net import (from external), < 0 means net export (to external)
                for i in range(n_periods):
                    problem += power_vars[i] == element.power_production[i] - element.power_consumption[i]
            else:
                # Battery: normal semantics
                # power_vars > 0 means net charge (from external), < 0 means net discharge (to external)
                for i in range(n_periods):
                    problem += power_vars[i] == element.power_consumption[i] - element.power_production[i]
        elif has_production:
            # PV: only production
            # PV produces power - treat as negative consumption (element provides to external)
            # power_vars < 0 when producing
            for i in range(n_periods):
                problem += -power_vars[i] == element.power_production[i]
        elif has_consumption:
            # Load: only consumption
            # Load consumes power FROM external (positive power_vars)
            for i in range(n_periods):
                problem += power_vars[i] == element.power_consumption[i]

        # Set objective
        problem += element.cost() + calculate_power_cost(power_vars, power_cost, period)

    # Solve
    status = solve_problem(problem)
    if status != 1:
        msg = f"Optimization failed with status {status}"
        raise ValueError(msg)

    # Extract outputs from element
    outputs = element.get_outputs()

    # Convert to dict format for comparison
    result = {}
    for name, output_data in outputs.items():
        result[name] = {
            "type": output_data.type,
            "unit": output_data.unit,
            "values": output_data.values,
        }

    return result

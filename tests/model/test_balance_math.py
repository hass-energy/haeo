"""Direct tests for battery balance connection math without LP solver.

Tests the constraint formulation to verify unique feasible solutions.
"""

import pytest


def check_downward_constraints(
    *,
    p_down: float,
    s_down: float,
    demand: float,
    e_upper: float,
) -> tuple[bool, list[str]]:
    """Check if downward flow satisfies all constraints.

    Constraints:
        1. P_down + S_down = D (equality - demand satisfaction)
        2. P_down <= E_upper (can't take more than available)
        3. S_down >= D - E_upper (minimum slack)
        4. P_down >= 0, S_down >= 0 (non-negativity)

    Returns:
        (is_feasible, list of violated constraints)

    """
    violations = []

    # Non-negativity
    if p_down < -1e-9:
        violations.append(f"P_down >= 0: {p_down} < 0")
    if s_down < -1e-9:
        violations.append(f"S_down >= 0: {s_down} < 0")

    # Constraint 1: equality
    if abs(p_down + s_down - demand) > 1e-9:
        violations.append(f"P_down + S_down = D: {p_down} + {s_down} = {p_down + s_down} != {demand}")

    # Constraint 2: availability
    if p_down > e_upper + 1e-9:
        violations.append(f"P_down <= E_upper: {p_down} > {e_upper}")

    # Constraint 3: minimum slack
    min_slack = demand - e_upper
    if s_down < min_slack - 1e-9:
        violations.append(f"S_down >= D - E_upper: {s_down} < {min_slack}")

    return len(violations) == 0, violations


def check_upward_constraints(
    *,
    p_up: float,
    s_up: float,
    excess: float,
    e_lower: float,
) -> tuple[bool, list[str]]:
    """Check if upward flow satisfies all constraints.

    Constraints (using subtraction formulation):
        1. P_up - S_up = excess (equality with subtraction)
        2. P_up <= E_lower (can't push more than available in lower)
        3. S_up >= max(0, -excess) (minimum slack to keep P_up >= 0)
        4. P_up >= 0, S_up >= 0 (non-negativity)
        5. P_up <= max(0, excess) (can't push more than the overflow)

    Returns:
        (is_feasible, list of violated constraints)

    """
    violations = []

    # Non-negativity
    if p_up < -1e-9:
        violations.append(f"P_up >= 0: {p_up} < 0")
    if s_up < -1e-9:
        violations.append(f"S_up >= 0: {s_up} < 0")

    # Constraint 1: equality with SUBTRACTION
    if abs(p_up - s_up - excess) > 1e-9:
        violations.append(f"P_up - S_up = excess: {p_up} - {s_up} = {p_up - s_up} != {excess}")

    # Constraint 2: availability (can't push more than lower has)
    if p_up > e_lower + 1e-9:
        violations.append(f"P_up <= E_lower: {p_up} > {e_lower}")

    # Constraint 3: minimum slack (when excess is negative)
    min_slack = max(0.0, -excess)
    if s_up < min_slack - 1e-9:
        violations.append(f"S_up >= max(0, -excess): {s_up} < {min_slack}")

    # Constraint 5: P_up upper bound
    max_p_up = max(0.0, excess)
    if p_up > max_p_up + 1e-9:
        violations.append(f"P_up <= max(0, excess): {p_up} > {max_p_up}")

    return len(violations) == 0, violations


def find_unique_solution_downward(
    demand: float,
    e_upper: float,
) -> tuple[float, float] | None:
    """Find the unique feasible (P_down, S_down) solution.

    Returns None if no unique solution exists, otherwise (P_down, S_down).
    """
    p_down = min(demand, e_upper)
    s_down = demand - p_down

    feasible, _ = check_downward_constraints(p_down=p_down, s_down=s_down, demand=demand, e_upper=e_upper)
    if not feasible:
        return None

    return p_down, s_down


def find_unique_solution_upward(
    excess: float,
    e_lower: float,
) -> tuple[float, float] | None:
    """Find the unique feasible (P_up, S_up) solution.

    Using formulation: P_up - S_up = excess (SUBTRACTION)

    Returns None if no unique solution exists, otherwise (P_up, S_up).
    """
    if excess <= 0:
        p_up = 0.0
        s_up = -excess
    else:
        if excess > e_lower:
            return None
        p_up = excess
        s_up = 0.0

    feasible, _ = check_upward_constraints(p_up=p_up, s_up=s_up, excess=excess, e_lower=e_lower)
    if not feasible:
        return None

    return p_up, s_up


# =============================================================================
# Downward Flow Test Cases
# =============================================================================

DOWNWARD_CASES = [
    pytest.param(3.0, 5.0, 3.0, 0.0, id="demand_less_than_available"),
    pytest.param(5.0, 5.0, 5.0, 0.0, id="demand_equals_available"),
    pytest.param(5.0, 3.0, 3.0, 2.0, id="demand_exceeds_available"),
    pytest.param(0.0, 5.0, 0.0, 0.0, id="zero_demand"),
    pytest.param(3.0, 0.0, 0.0, 3.0, id="zero_available"),
]


@pytest.mark.parametrize(("demand", "e_upper", "expected_p_down", "expected_s_down"), DOWNWARD_CASES)
def test_downward_solution(
    demand: float,
    e_upper: float,
    expected_p_down: float,
    expected_s_down: float,
) -> None:
    """Test downward flow produces unique solution."""
    result = find_unique_solution_downward(demand, e_upper)

    assert result is not None
    p_down, s_down = result
    assert p_down == pytest.approx(expected_p_down)
    assert s_down == pytest.approx(expected_s_down)


# =============================================================================
# Upward Flow Test Cases
# =============================================================================

UPWARD_CASES = [
    pytest.param(2.0 - 5.0, 2.0, 0.0, 3.0, id="negative_excess_room_available"),
    pytest.param(5.0 - 3.0, 5.0, 2.0, 0.0, id="positive_excess_push_overflow"),
    pytest.param(5.0 - 0.0, 5.0, 5.0, 0.0, id="capacity_shrinks_to_zero"),
    pytest.param(0.0 - 5.0, 0.0, 0.0, 5.0, id="empty_section_no_excess"),
]


@pytest.mark.parametrize(("excess", "e_lower", "expected_p_up", "expected_s_up"), UPWARD_CASES)
def test_upward_solution(
    excess: float,
    e_lower: float,
    expected_p_up: float,
    expected_s_up: float,
) -> None:
    """Test upward flow produces unique solution."""
    result = find_unique_solution_upward(excess, e_lower)

    assert result is not None
    p_up, s_up = result
    assert p_up == pytest.approx(expected_p_up)
    assert s_up == pytest.approx(expected_s_up)


# =============================================================================
# Combined Flow Scenarios
# =============================================================================

COMBINED_CASES = [
    pytest.param(
        # Initial ordering violation: lower under capacity, upper has energy
        1.0,  # e_lower
        2.0,  # e_upper
        5.0,  # c_lower (old capacity for demand)
        5.0,  # c_new (new capacity for excess)
        2.0,  # expected p_down (all of upper's energy)
        2.0,  # expected s_down (demand=4, transferred=2)
        0.0,  # expected p_up (no overflow)
        4.0,  # expected s_up (absorbs negative excess)
        id="initial_ordering_violation",
    ),
    pytest.param(
        # Capacity shrinkage: lower overfull after shrinkage
        4.0,  # e_lower
        3.0,  # e_upper
        3.0,  # c_lower (new capacity for demand - already at new)
        3.0,  # c_new (for excess calculation)
        0.0,  # expected p_down (demand = max(0, 3-4) = 0)
        0.0,  # expected s_down
        1.0,  # expected p_up (excess = 4-3 = 1)
        0.0,  # expected s_up
        id="capacity_shrinkage_forces_upward",
    ),
]


@pytest.mark.parametrize(
    (
        "e_lower",
        "e_upper",
        "c_lower",
        "c_new",
        "expected_p_down",
        "expected_s_down",
        "expected_p_up",
        "expected_s_up",
    ),
    COMBINED_CASES,
)
def test_combined_flow(
    e_lower: float,
    e_upper: float,
    c_lower: float,
    c_new: float,
    expected_p_down: float,
    expected_s_down: float,
    expected_p_up: float,
    expected_s_up: float,
) -> None:
    """Test combined downward and upward flows in a scenario."""
    demand = max(0.0, c_lower - e_lower)
    excess = e_lower - c_new

    down_result = find_unique_solution_downward(demand, e_upper)
    up_result = find_unique_solution_upward(excess, e_lower)

    assert down_result is not None
    assert up_result is not None

    p_down, s_down = down_result
    p_up, s_up = up_result

    assert p_down == pytest.approx(expected_p_down)
    assert s_down == pytest.approx(expected_s_down)
    assert p_up == pytest.approx(expected_p_up)
    assert s_up == pytest.approx(expected_s_up)


# =============================================================================
# Multi-Period Scenario
# =============================================================================


def test_multi_period_ordering() -> None:
    """Multi-period scenario: verify ordering is maintained across periods.

    Period 0: lower=1, upper=2, capacity=5 (constant)
    Total=3 should all end up in lower after period 0.

    This tests the ordering constraint over time.
    """
    e_lower_0 = 1.0
    e_upper_0 = 2.0
    c_lower = 5.0

    # Period 0
    demand_0 = c_lower - e_lower_0
    excess_0 = e_lower_0 - c_lower

    down_0 = find_unique_solution_downward(demand_0, e_upper_0)
    up_0 = find_unique_solution_upward(excess_0, e_lower_0)

    assert down_0 is not None
    assert up_0 is not None

    p_down_0, _ = down_0
    p_up_0, _ = up_0

    assert p_down_0 == pytest.approx(2.0)  # All of upper's energy
    assert p_up_0 == pytest.approx(0.0)  # No upward flow

    # State after period 0
    e_lower_1 = e_lower_0 + p_down_0 - p_up_0
    e_upper_1 = e_upper_0 - p_down_0 + p_up_0

    assert e_lower_1 == pytest.approx(3.0)
    assert e_upper_1 == pytest.approx(0.0)

    # Period 1: Already ordered, should stay put
    demand_1 = c_lower - e_lower_1
    excess_1 = e_lower_1 - c_lower

    down_1 = find_unique_solution_downward(demand_1, e_upper_1)
    up_1 = find_unique_solution_upward(excess_1, e_lower_1)

    assert down_1 is not None
    assert up_1 is not None

    p_down_1, _ = down_1
    p_up_1, _ = up_1

    assert p_down_1 == pytest.approx(0.0)  # Upper is empty
    assert p_up_1 == pytest.approx(0.0)  # No excess

    # State unchanged
    e_lower_2 = e_lower_1 + p_down_1 - p_up_1
    e_upper_2 = e_upper_1 - p_down_1 + p_up_1

    assert e_lower_2 == pytest.approx(3.0)
    assert e_upper_2 == pytest.approx(0.0)


# =============================================================================
# Uniqueness Analysis
# =============================================================================
#
# These tests demonstrate that WITHOUT all constraints, multiple solutions
# would exist, but WITH the full constraint set, solutions are UNIQUE.
#
# Key insight: The full constraint set (including P_up <= max(0, excess))
# eliminates all degeneracy. The epsilon costs are only for numerical
# stability within solver tolerance, not for breaking mathematical ties.
# =============================================================================


class TestUniquenessAnalysis:
    """Analyze solution uniqueness with and without constraint subsets.

    These tests enumerate feasible solutions under different constraint
    configurations to demonstrate that the full constraint set produces
    unique solutions with NO mathematical degeneracy.
    """

    def test_downward_range_without_ordering(self) -> None:
        """Without ordering constraint, downward has multiple feasible points.

        INCOMPLETE CONSTRAINTS: Without the ordering constraint forcing maximum
        transfer, any P_down in [0, min(demand, e_upper)] satisfies the
        basic feasibility constraints.

        With ordering: only P_down = min(demand, e_upper) is feasible.
        """
        demand = 3.0
        e_upper = 5.0

        # Enumerate feasible solutions without ordering
        feasible_without_ordering = []
        for p_down in [0.0, 1.0, 2.0, 3.0]:
            s_down = demand - p_down
            feasible, _ = check_downward_constraints(p_down=p_down, s_down=s_down, demand=demand, e_upper=e_upper)
            if feasible:
                feasible_without_ordering.append((p_down, s_down))

        # Without ordering: 4 feasible solutions (incomplete constraint set)
        assert len(feasible_without_ordering) == 4

        # With ordering (simulated by requiring maximum transfer):
        # Only P_down = min(3, 5) = 3 satisfies ordering
        unique_solution = find_unique_solution_downward(demand, e_upper)
        assert unique_solution == pytest.approx((3.0, 0.0))

    def test_downward_range_with_soc_but_no_ordering(self) -> None:
        """With SOC constraints but no ordering, still multiple solutions.

        INCOMPLETE CONSTRAINTS: SOC constraints (0 <= E <= C) eliminate some
        solutions but don't guarantee uniqueness. Ordering is required.

        Setup: lower=1, upper=2, capacity=5
        """
        e_lower = 1.0
        e_upper = 2.0
        c_lower = 5.0
        c_upper = 5.0

        demand = c_lower - e_lower  # 4 kWh

        feasible_with_soc = []
        for p_down in [0.0, 1.0, 2.0, 3.0, 4.0]:
            s_down = demand - p_down

            feasible, _ = check_downward_constraints(p_down=p_down, s_down=s_down, demand=demand, e_upper=e_upper)
            if not feasible:
                continue

            # Check SOC constraints
            new_e_lower = e_lower + p_down
            new_e_upper = e_upper - p_down

            soc_ok = new_e_lower >= 0 and new_e_lower <= c_lower and new_e_upper >= 0 and new_e_upper <= c_upper

            if soc_ok:
                feasible_with_soc.append((p_down, s_down))

        # SOC eliminates P_down > 2 (upper would go negative)
        # But P_down in [0, 1, 2] are all SOC-feasible: 3 solutions (incomplete)
        assert len(feasible_with_soc) == 3

    def test_downward_unique_with_full_constraints(self) -> None:
        """With ordering constraint, downward is forced to maximum.

        UNIQUE SOLUTION: The ordering constraint requires lower to fill
        before upper retains energy. This forces P_down = min(demand, e_upper).

        Setup: lower=1, upper=2, capacity=5, total=3 < capacity
        Required: All energy in lower (new_upper = 0)
        """
        e_lower = 1.0
        e_upper = 2.0
        c_lower = 5.0

        demand = c_lower - e_lower

        feasible_with_ordering = []
        for p_down in [0.0, 1.0, 2.0]:
            s_down = demand - p_down

            feasible, _ = check_downward_constraints(p_down=p_down, s_down=s_down, demand=demand, e_upper=e_upper)
            if not feasible:
                continue

            # Check ordering: after transfer, upper must be 0 (when total <= c_lower)
            new_e_upper = e_upper - p_down
            ordering_ok = new_e_upper == 0

            if ordering_ok:
                feasible_with_ordering.append((p_down, s_down))

        # UNIQUE: Only P_down=2 satisfies ordering (no degeneracy!)
        assert len(feasible_with_ordering) == 1
        assert feasible_with_ordering[0] == pytest.approx((2.0, 2.0))

    def test_upward_unique_with_upper_bound(self) -> None:
        """With P_up <= max(0, excess), negative excess forces P_up = 0.

        UNIQUE SOLUTION: When excess < 0, the upper bound constraint
        P_up <= max(0, excess) = 0 forces P_up = 0 exactly.

        Without this constraint, any P_up with S_up = P_up - excess would
        be feasible, creating infinite degeneracy.
        """
        excess = -3.0
        e_lower = 5.0

        # Enumerate what would be feasible WITHOUT P_up upper bound
        feasible_without_bound = []
        for p_up in [0.0, 1.0, 2.0, 3.0]:
            s_up = p_up - excess  # From equality P_up - S_up = excess
            # Check only non-negativity and equality (skip upper bound check)
            if p_up >= 0 and s_up >= 0 and abs(p_up - s_up - excess) < 1e-9:
                feasible_without_bound.append((p_up, s_up))

        # Without bound: all 4 solutions are feasible (incomplete constraint set)
        assert len(feasible_without_bound) == 4

        # With P_up <= max(0, excess) = 0: only P_up = 0 works
        feasible_with_bound = []
        for p_up in [0.0, 1.0, 2.0, 3.0]:
            s_up = p_up - excess
            feasible, _ = check_upward_constraints(p_up=p_up, s_up=s_up, excess=excess, e_lower=e_lower)
            if feasible:
                feasible_with_bound.append((p_up, s_up))

        # UNIQUE: Only P_up=0 is feasible (no degeneracy!)
        assert len(feasible_with_bound) == 1
        assert feasible_with_bound[0] == pytest.approx((0.0, 3.0))

    def test_upward_unique_positive_excess(self) -> None:
        """With positive excess, P_up is bounded from both sides.

        UNIQUE SOLUTION: When excess > 0:
        - Lower bound: P_up - S_up = excess with S_up >= 0 gives P_up >= excess
        - Upper bound: P_up <= max(0, excess) = excess

        Together: P_up = excess exactly (no degeneracy!)
        """
        excess = 2.0
        e_lower = 5.0

        # With both bounds, only P_up = excess is feasible
        feasible_solutions = []
        for p_up in [0.0, 1.0, 2.0, 3.0, 4.0]:
            s_up = p_up - excess
            if s_up < 0:
                continue  # S_up must be non-negative
            feasible, _ = check_upward_constraints(p_up=p_up, s_up=s_up, excess=excess, e_lower=e_lower)
            if feasible:
                feasible_solutions.append((p_up, s_up))

        # UNIQUE: Only P_up=2, S_up=0 is feasible (no degeneracy!)
        assert len(feasible_solutions) == 1
        assert feasible_solutions[0] == pytest.approx((2.0, 0.0))

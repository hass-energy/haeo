"""Test that HiGHS presolve efficiently handles equality constraint chains.

This verifies that composing connections via chained segments with equality
constraints doesn't degrade solver performance.
"""

import time

from highspy import Highs
from highspy.highs import HighspyArray


def test_equality_chain_solve_time_scaling() -> None:
    """Verify solve time doesn't significantly increase with chain length.

    Compares solve time between 1-segment and 5-segment chains.
    With good presolve, both should solve in similar time.
    """
    n_periods = 48
    n_runs = 3

    def solve_chain(chain_length: int) -> float:
        """Create and solve a chain, return solve time."""
        h = Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("log_to_console", False)

        segments: list[tuple[HighspyArray, HighspyArray]] = []
        for i in range(chain_length):
            power_in = h.addVariables(n_periods, lb=0, ub=10.0, name_prefix=f"seg{i}_in_", out_array=True)
            power_out = h.addVariables(n_periods, lb=0, ub=10.0, name_prefix=f"seg{i}_out_", out_array=True)
            segments.append((power_in, power_out))
            h.addConstrs(power_out == power_in)

        for i in range(chain_length - 1):
            h.addConstrs(segments[i][1] == segments[i + 1][0])

        # Add a cost term to make it interesting
        h.minimize(Highs.qsum(segments[0][0]) - 0.5 * Highs.qsum(segments[-1][1]))

        start = time.perf_counter()
        h.run()
        return time.perf_counter() - start

    # Warm up
    solve_chain(1)

    # Time both configurations
    time_1_seg = min(solve_chain(1) for _ in range(n_runs))
    time_5_seg = min(solve_chain(5) for _ in range(n_runs))

    # 5-segment chain should solve in less than 3x the time of 1-segment
    # (allowing for some overhead, but not linear scaling with chain length)
    ratio = time_5_seg / max(time_1_seg, 1e-6)
    assert ratio < 3.0, f"5-segment chain took {ratio:.1f}x longer than 1-segment (expected < 3x)"

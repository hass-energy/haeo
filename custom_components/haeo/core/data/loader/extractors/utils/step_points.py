"""Points for forecast values that describe a period."""

from collections.abc import Iterable, Sequence


def step_points(blocks: Iterable[tuple[int, int, float]]) -> list[tuple[int, float]]:
    """Return points that hold each block's value from its start to its end.

    Each (start, end, value) block emits (start, value) and (end, value), so the
    fuser's linear interpolation keeps the value constant across the block.
    Adjacent blocks share a boundary timestamp, which ``extract()`` separates so
    the series steps there instead of ramping.
    """
    return [point for start, end, value in sorted(blocks) for point in ((start, value), (end, value))]


def hold_until_next(points: Sequence[tuple[int, float]]) -> list[tuple[int, int, float]]:
    """Return blocks that hold each point's value until the next point.

    The last point holds for as long as the step before it, so at least two
    points are needed.
    """
    ordered = sorted(points)
    ends = [end for end, _ in ordered[1:]]
    ends.append(2 * ordered[-1][0] - ordered[-2][0])
    return [(start, end, value) for (start, value), end in zip(ordered, ends, strict=True)]


def period_means(blocks: Iterable[tuple[int, int, float]]) -> list[tuple[int, float]]:
    """Return points for the means of a smoothly varying quantity over periods.

    Each mean sits at the middle of its period, where a smoothly varying
    quantity equals its mean, so the fuser's interpolation between midpoints
    recovers the period means. The first and last means also hold out to the
    start of the first period and the end of the last, so the points cover
    every period rather than leaving the edges to the fuser's cycling.
    """
    ordered = sorted(blocks)
    (first_start, _, first_mean), (_, last_end, last_mean) = ordered[0], ordered[-1]
    return [
        (first_start, first_mean),
        *(((start + end) // 2, mean) for start, end, mean in ordered),
        (last_end, last_mean),
    ]

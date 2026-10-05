"""Print selected output series side by side, aligned on time.

Explaining a decision means comparing what the optimizer did against what it was
seeing at that moment. The forecast series are all in the export but scattered
across entities, so this lines the requested ones up in a single table.
"""

from collections.abc import Mapping, Sequence
import re
from typing import Any, Final

NAME: Final = "series"
HELP: Final = "Time-aligned table of output series matching a regex (arg: regex, default all)"

LABEL_WIDTH: Final = 14
MAX_ROWS: Final = 40


def forecast_series(entity: Mapping[str, Any]) -> dict[str, float]:
    """Return {HH:MM: value} for an entity's forecast, empty when it has none."""
    points = entity.get("attributes", {}).get("forecast") or []
    result: dict[str, float] = {}
    for point in points:
        time, value = point.get("time"), point.get("value")
        if isinstance(time, str) and isinstance(value, int | float) and not isinstance(value, bool):
            result[time[11:16]] = float(value)
    return result


def column_labels(entity_ids: Sequence[str], limit: int = LABEL_WIDTH) -> dict[str, str]:
    """Map entity ids to short column labels by dropping the parts they all share.

    Shadow-price columns otherwise collapse to identical suffixes, so strip the
    common leading and trailing name segments before truncating.
    """
    stems = [entity_id.split(".", 1)[-1] for entity_id in entity_ids]
    if len(stems) == 1:
        return {entity_ids[0]: stems[0]}

    split = [stem.split("_") for stem in stems]
    head = 0
    while all(len(parts) > head + 1 and parts[head] == split[0][head] for parts in split):
        head += 1
    tail = 0
    while all(len(parts) > head + tail + 1 and parts[-1 - tail] == split[0][-1 - tail] for parts in split):
        tail += 1

    cores = ["_".join(parts[head : len(parts) - tail]) or "_".join(parts) for parts in split]

    # Widen only as far as needed to keep every column distinguishable.
    for width in (limit, limit + 4, limit + 10):
        candidate = [core[:width] for core in cores]
        if len(set(candidate)) == len(candidate):
            return dict(zip(entity_ids, candidate, strict=True))

    # Any truncation would make two columns look identical; number them instead.
    return {entity_id: f"c{index + 1}" for index, entity_id in enumerate(entity_ids)}


def run(outputs: Mapping[str, Any], config: Mapping[str, Any], argument: str) -> str:  # noqa: ARG001 (config unused; the analysis interface is uniform across modules)
    """Return a time-aligned table of the output series matching `argument`."""
    try:
        pattern = re.compile(argument or ".", re.IGNORECASE)
    except re.error as err:
        return f"series: {argument!r} is not a valid regex ({err.msg} at position {err.pos})"

    matched = sorted(entity_id for entity_id in outputs if pattern.search(entity_id))
    if not matched:
        return f"series: no entity ids match {argument or '.'!r}"

    columns = {entity_id: points for entity_id in matched if (points := forecast_series(outputs[entity_id]))}
    skipped = [entity_id for entity_id in matched if entity_id not in columns]
    if not columns:
        listing = "\n".join(f"  {entity_id} (state={outputs[entity_id].get('state')})" for entity_id in skipped)
        return f"series: matched entities have no forecast series\n{listing}"

    labels = column_labels(list(columns))
    width = max(9, *(len(label) for label in labels.values()))

    lines = ["columns:"]
    lines += [f"  {labels[entity_id]:>{width}}  {entity_id}" for entity_id in columns]
    if skipped:
        lines += [f"  {'(no forecast)':>{width}}  {entity_id}" for entity_id in skipped]
    lines.append("")

    header = f"{'time':>6} " + " ".join(f"{labels[entity_id]:>{width}}" for entity_id in columns)
    lines += [header, "-" * len(header)]

    times = sorted({time for points in columns.values() for time in points})
    for time in times[:MAX_ROWS]:
        cells = [
            f"{value:>{width}.4f}" if (value := points.get(time)) is not None else " " * (width - 1) + "-"
            for points in columns.values()
        ]
        lines.append(f"{time:>6} " + " ".join(cells))
    if len(times) > MAX_ROWS:
        lines.append(f"... {len(times) - MAX_ROWS} more intervals")

    return "\n".join(lines)

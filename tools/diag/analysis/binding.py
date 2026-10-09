"""Report which constraints were binding, and when.

This is the first question to ask about any optimizer decision: was it forced or
chosen? A shadow price is zero when its constraint is slack and non-zero when it
binds, so scanning the duals splits the plan into "a limit stopped it" — naming
which limit — and "nothing was in the way, so it was economic".
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from .series import forecast_series

NAME: Final = "binding"
HELP: Final = "Which constraints bind, and when (arg: tolerance in $/kWh, default 1e-6)"

SHADOW_SUFFIX: Final = "_shadow_price"
DEFAULT_TOLERANCE: Final = 1e-6
MAX_INTERVALS_SHOWN: Final = 6

# Balance duals price energy at a point and are non-zero almost everywhere, so
# they explain economics rather than indicating a limit was hit.
BALANCE_MARKERS: Final = ("_power_balance",)

# Forecast limits bind by construction: load must be met and generation cannot
# exceed its forecast. Their duals say what more of that resource would be worth,
# not that the optimizer was denied a choice it wanted.
FORECAST_MARKERS: Final = ("_forecast_limit",)


def _category(entity_id: str) -> str:
    if any(marker in entity_id for marker in BALANCE_MARKERS):
        return "balance"
    if any(marker in entity_id for marker in FORECAST_MARKERS):
        return "forecast"
    return "capacity"


def _summarize(times: Sequence[str]) -> str:
    if len(times) <= MAX_INTERVALS_SHOWN:
        return ", ".join(times)
    shown = ", ".join(times[:MAX_INTERVALS_SHOWN])
    return f"{shown}, +{len(times) - MAX_INTERVALS_SHOWN} more"


def run(outputs: Mapping[str, Any], config: Mapping[str, Any], argument: str) -> str:  # noqa: ARG001 (config unused; the analysis interface is uniform across modules)
    """Return a summary of which constraints bind over the horizon."""
    try:
        tolerance = float(argument) if argument else DEFAULT_TOLERANCE
    except ValueError:
        return f"binding: tolerance must be a number, got {argument!r}"

    # A negative tolerance passes every dual, including exact zeros, which would
    # report slack constraints as forced decisions.
    if tolerance < 0:
        return f"binding: tolerance must not be negative, got {tolerance:g}"

    shadow_ids = sorted(entity_id for entity_id in outputs if entity_id.endswith(SHADOW_SUFFIX))
    if not shadow_ids:
        return "binding: the export contains no shadow-price entities"

    binding_by_category: dict[str, list[str]] = {"capacity": [], "forecast": [], "balance": []}
    slack: list[str] = []

    for entity_id in shadow_ids:
        points = forecast_series(outputs[entity_id])
        active = {time: value for time, value in points.items() if abs(value) > tolerance}
        label = entity_id.removeprefix("sensor.").removesuffix(SHADOW_SUFFIX)

        if not active:
            slack.append(label)
            continue

        times = sorted(active)
        low, high = min(active.values()), max(active.values())
        span = f"{low:.4f}" if low == high else f"{low:.4f} to {high:.4f}"
        entry = f"  {label}\n      {len(active)}/{len(points)} intervals, {span} $/kWh\n      {_summarize(times)}"
        binding_by_category[_category(entity_id)].append(entry)

    lines = [f"Binding constraints (|dual| > {tolerance:g} $/kWh)", ""]

    if binding_by_category["capacity"]:
        lines += [
            "CAPACITY LIMITS REACHED — the optimizer was forced here:",
            *binding_by_category["capacity"],
            "",
        ]
    else:
        lines += [
            "CAPACITY LIMITS REACHED — none.",
            "  No power or state-of-charge limit binds anywhere in the horizon, so nothing",
            "  physical constrained the plan. Every decision was economic; explain it as a",
            "  price comparison rather than as a limit.",
            "",
        ]

    if binding_by_category["forecast"]:
        lines += [
            "FORECAST LIMITS — bind by construction, so this is expected:",
            "  The dual is what an extra kWh of that resource would have been worth,",
            "  not evidence the optimizer was denied a choice.",
            *binding_by_category["forecast"],
            "",
        ]

    if binding_by_category["balance"]:
        lines += ["MARGINAL ENERGY VALUE — what power is worth at each point:", *binding_by_category["balance"], ""]

    if slack:
        lines += ["SLACK THROUGHOUT — never limited the plan:", "  " + ", ".join(slack), ""]

    lines += [
        "Note: not every limit publishes a dual. Where a flow sits exactly at its",
        "configured maximum but no dual appears here, check the limit directly.",
    ]
    return "\n".join(lines)

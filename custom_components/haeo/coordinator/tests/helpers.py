"""Helpers shared by the coordinator tests."""

from collections.abc import Awaitable, Callable
import json
from pathlib import Path
from typing import Any  # noqa: TID251  # Mock-typed horizon manager and JSON read back from a diagnostics file
from unittest.mock import MagicMock, Mock

from homeassistant.core import HomeAssistant

from custom_components.haeo import HaeoRuntimeData

# Placeholders of an issue raised by an earlier optimization
EARLIER_ISSUE = {
    "elements": "Earlier Load",
    "minutes": "45",
    "planned_at": "08:00",
    "relaxed_elements": "Earlier Load",
    "relaxed_periods": "1",
}
EARLIER_DIAGNOSTICS = "/config/haeo/diagnostics/earlier.json"

# Period lengths of the mock horizon, between its forecast timestamps
MOCK_PERIODS_SECONDS = [1000, 1000]


def network_double() -> MagicMock:
    """Return a network double built for the mock horizon's periods."""
    network = MagicMock()
    network.n_periods = len(MOCK_PERIODS_SECONDS)
    return network


def run_jobs_but(hass: HomeAssistant, skipped: object, result: object) -> Callable[..., Awaitable[object]]:
    """Return an executor stand-in that runs every job but ``skipped``, which returns ``result`` instead."""
    run = hass.async_add_executor_job

    async def run_job(target: Callable[..., object], *args: object) -> object:
        if target is skipped:
            return result
        return await run(target, *args)

    return run_job


def saved_diagnostics(hass: HomeAssistant, path: str, kind: str) -> dict[str, Any]:
    """Read a diagnostics file saved for a failed or relaxed plan, checking where it was saved."""
    saved = Path(path)
    if saved.parent != Path(hass.config.path("haeo", "diagnostics")) or not saved.name.startswith(f"{kind}_"):
        msg = f"{kind} diagnostics were saved to {path}"
        raise AssertionError(msg)
    return json.loads(saved.read_text())


def mock_horizon(runtime_data: HaeoRuntimeData) -> Any:
    """Return the mock horizon manager of the ``mock_runtime_data`` fixture, typed for its mock methods."""
    return runtime_data.horizon_manager


def source_state(unit: str) -> Mock:
    """Create a mock source entity state with a unit_of_measurement attribute."""
    return Mock(attributes={"unit_of_measurement": unit})

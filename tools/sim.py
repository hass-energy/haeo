"""Realtime Home Assistant simulator driven by scenario inputs.

Boots a live in-process Home Assistant instance, feeds time-shifted scenario
input states on an interval, optionally configures HAEO from the scenario config,
and tears down on Ctrl+C.

Usage:
    uv run sim scenario1
    uv run sim tests/scenarios/scenario1 --interval 30 --speed 60
    uv run sim scenario1 --no-config
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
import signal
import sys
import time
from typing import Any, TypedDict
import webbrowser
from zoneinfo import ZoneInfo

from freezegun import freeze_time

from tools.live_hass import LiveHomeAssistant
from tools.sim_hass import live_sim_home_assistant, setup_haeo_entry, wait_for_sim_idle
from tools.time_shift import parse_anchor_timestamp, shift_timestamps

PROJECT_ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = PROJECT_ROOT / "tests" / "scenarios"
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
DEFAULT_PORT = 8123

_LOGGER = logging.getLogger(__name__)


class ScenarioFiles(TypedDict):
    """Paths and data for a scenario directory."""

    path: Path
    config: dict[str, Any]
    environment: dict[str, Any]
    inputs: list[dict[str, Any]]


def resolve_scenario_path(scenario: str) -> Path:
    """Resolve a scenario name or path to a scenario directory."""
    candidate = Path(scenario)
    if candidate.is_dir():
        return candidate.resolve()

    scenarios_candidate = SCENARIOS_DIR / scenario
    if scenarios_candidate.is_dir():
        return scenarios_candidate.resolve()

    msg = f"Scenario not found: {scenario}"
    raise FileNotFoundError(msg)


def load_scenario(scenario: str) -> ScenarioFiles:
    """Load scenario JSON files from a scenario directory."""
    scenario_path = resolve_scenario_path(scenario)
    config = json.loads((scenario_path / "config.json").read_text(encoding="utf-8"))
    environment = json.loads((scenario_path / "environment.json").read_text(encoding="utf-8"))
    inputs = json.loads((scenario_path / "inputs.json").read_text(encoding="utf-8"))
    return {
        "path": scenario_path,
        "config": config,
        "environment": environment,
        "inputs": inputs,
    }


def prepare_shifted_states(inputs: list[dict[str, Any]], delta: timedelta) -> list[dict[str, Any]]:
    """Return HA state dicts with timestamp fields shifted by delta."""
    return [
        {
            "entity_id": state_data["entity_id"],
            "state": state_data["state"],
            "attributes": shift_timestamps(state_data.get("attributes", {}), delta),
        }
        for state_data in inputs
    ]


def compute_sim_now(
    *,
    anchor: datetime,
    timezone: str,
    speed: float,
    started_at: float,
) -> datetime:
    """Compute the simulated current time for this tick."""
    if speed == 1.0:
        return datetime.now(ZoneInfo(timezone))

    elapsed_seconds = (time.monotonic() - started_at) * speed
    simulated = anchor + timedelta(seconds=elapsed_seconds)
    if simulated.tzinfo is None:
        return simulated.replace(tzinfo=ZoneInfo(timezone))
    return simulated.astimezone(ZoneInfo(timezone))


def run_sim_loop(
    live_hass: LiveHomeAssistant,
    *,
    inputs: list[dict[str, Any]],
    anchor: datetime,
    timezone: str,
    interval: float,
    speed: float,
    time_freezer: Any | None,
) -> None:
    """Push shifted scenario states until interrupted."""
    started_at = time.monotonic()
    stop = False

    def _handle_signal(_signum: int, _frame: Any) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    while not stop:
        sim_now = compute_sim_now(
            anchor=anchor,
            timezone=timezone,
            speed=speed,
            started_at=started_at,
        )
        if time_freezer is not None:
            time_freezer.move_to(sim_now)

        delta = sim_now - anchor.astimezone(sim_now.tzinfo)
        shifted_states = prepare_shifted_states(inputs, delta)
        live_hass.set_states(shifted_states)
        _LOGGER.info("Updated %d input states at simulated time %s", len(shifted_states), sim_now.isoformat())

        deadline = time.monotonic() + interval
        while not stop and time.monotonic() < deadline:
            time.sleep(0.2)


def run_sim(
    scenario: str,
    *,
    interval: float,
    speed: float,
    with_config: bool,
    config_dir: Path | None,
    port: int | None,
    open_browser: bool,
) -> None:
    """Boot live HA, optionally configure HAEO, and run the realtime input loop."""
    scenario_data = load_scenario(scenario)
    anchor = parse_anchor_timestamp(scenario_data["environment"]["optimization_start_time"])
    timezone = scenario_data["environment"]["timezone"]

    time_freezer = None
    if speed != 1.0:
        time_freezer = freeze_time(anchor)
        time_freezer.start()
        _LOGGER.warning(
            "Accelerated time mode (--speed=%s) is experimental; recorder and debouncers may behave unexpectedly",
            speed,
        )

    try:
        with live_sim_home_assistant(
            timeout=120,
            config_dir=config_dir,
            port=port,
            environment=scenario_data["environment"],
        ) as live_hass:
            if with_config:
                live_hass.run_coro(setup_haeo_entry(live_hass.hass, scenario_data["config"]))
                _LOGGER.info("HAEO configured from %s", scenario_data["path"].name)

            # Let any in-flight setup/reload work finish before opening the browser.
            live_hass.run_coro(wait_for_sim_idle(live_hass.hass))

            # The trusted_networks auth provider auto-logs in from loopback, so
            # opening the root URL is enough; no token bootstrap is required.
            home_url = f"{live_hass.url}/"

            print(f"Home Assistant: {home_url}")
            print("Login: automatic from loopback (fallback: testuser / testpass)")
            print(f"Scenario: {scenario_data['path'].name}")
            print(f"Timezone: {timezone}")
            print(f"Config dir: {config_dir if config_dir is not None else 'ephemeral'}")
            print(f"Interval: {interval}s, speed: {speed}x")
            print("Press Ctrl+C to stop.")

            if open_browser:
                webbrowser.open(home_url)

            run_sim_loop(
                live_hass,
                inputs=scenario_data["inputs"],
                anchor=anchor,
                timezone=timezone,
                interval=interval,
                speed=speed,
                time_freezer=time_freezer,
            )
    finally:
        if time_freezer is not None:
            time_freezer.stop()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a live Home Assistant instance with time-shifted scenario inputs",
    )
    parser.add_argument(
        "scenario",
        nargs="?",
        default="scenario1",
        help="Scenario name under tests/scenarios/ or path to a scenario directory (default: scenario1)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Seconds between input state updates (default: 60)",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Simulated time multiplier; 1.0 uses wall clock, >1 accelerates (default: 1.0)",
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        help="Skip automatic HAEO configuration from scenario config.json",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the browser to the auto-login page on startup",
    )
    parser.add_argument(
        "--ephemeral",
        action="store_true",
        help="Use a temporary config directory and ephemeral port instead of config/ on port 8123",
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=None,
        help=f"Home Assistant config directory (default: {DEFAULT_CONFIG_DIR.relative_to(PROJECT_ROOT)})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=f"HTTP port (default: {DEFAULT_PORT})",
    )
    return parser


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = _build_parser()
    args = parser.parse_args()

    if args.interval <= 0:
        parser.error("--interval must be positive")
    if args.speed <= 0:
        parser.error("--speed must be positive")

    scenario = args.scenario
    candidate = Path(scenario)
    if not candidate.is_dir() and not (SCENARIOS_DIR / scenario).is_dir():
        _LOGGER.error("Scenario not found: %s", scenario)
        return 1

    if args.ephemeral:
        config_dir = None
        port = args.port
    else:
        config_dir = args.config_dir or DEFAULT_CONFIG_DIR
        port = args.port if args.port is not None else DEFAULT_PORT

    try:
        run_sim(
            scenario,
            interval=args.interval,
            speed=args.speed,
            with_config=not args.no_config,
            config_dir=config_dir,
            port=port,
            open_browser=not args.no_open,
        )
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())

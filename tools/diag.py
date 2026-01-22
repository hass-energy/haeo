#!/usr/bin/env python3
"""CLI tool to run HAEO optimization from a diagnostics JSON file.

Usage:
    uv run diag --file path/to/diagnostics.json
    uv run diag --file path/to/diagnostics.json --outputs-only

This tool loads a HAEO diagnostics export and either:
- Runs the optimization and displays results (default)
- Displays pre-computed outputs from the diagnostics file (--outputs-only)
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from tabulate import tabulate

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.data.util import ForecastSeries
from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals
from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, is_element_type
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import ModelElementConfig
from custom_components.haeo.model.output_data import OutputData


@dataclass
class DiagnosticsData:
    """Parsed diagnostics data."""

    config: dict[str, Any]
    environment: dict[str, Any]
    inputs: list[dict[str, Any]]
    outputs: dict[str, Any]

    @classmethod
    def from_file(cls, path: Path) -> DiagnosticsData:
        """Load diagnostics from a JSON file.

        Supports both unified format (with "data" wrapper) and split format.
        """
        with path.open() as f:
            data = json.load(f)

        # Check if this is a unified format with "data" wrapper
        if "data" in data and isinstance(data["data"], dict):
            data = data["data"]

        return cls(
            config=data.get("config", {}),
            environment=data.get("environment", {}),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", {}),
        )

    @classmethod
    def from_split_files(cls, directory: Path) -> DiagnosticsData:
        """Load diagnostics from split JSON files (config.json, environment.json, etc.)."""
        config_file = directory / "config.json"
        environment_file = directory / "environment.json"
        inputs_file = directory / "inputs.json"
        outputs_file = directory / "outputs.json"

        with config_file.open() as f:
            config = json.load(f)
        with environment_file.open() as f:
            environment = json.load(f)
        with inputs_file.open() as f:
            inputs = json.load(f)

        outputs: dict[str, Any] = {}
        if outputs_file.exists():
            with outputs_file.open() as f:
                outputs = json.load(f)

        return cls(config=config, environment=environment, inputs=inputs, outputs=outputs)


def parse_datetime_to_timestamp(value: str | datetime) -> float:
    """Parse a datetime string or datetime object to a Unix timestamp."""
    if isinstance(value, datetime):
        return value.timestamp()
    # Try parsing ISO format
    dt = datetime.fromisoformat(value)
    return dt.timestamp()


def extract_forecast_from_entity(entity_state: dict[str, Any]) -> tuple[float | None, ForecastSeries]:
    """Extract forecast data from an entity state dict.

    Returns:
        Tuple of (present_value, forecast_series) where forecast_series is
        a list of (timestamp, value) tuples.

    """
    state = entity_state.get("state")
    attributes = entity_state.get("attributes", {})
    forecast = attributes.get("forecast", [])

    # Try to get present value from state
    present_value: float | None = None
    if state is not None:
        with contextlib.suppress(ValueError, TypeError):
            present_value = float(state)

    # Parse forecast data
    forecast_series: ForecastSeries = []
    if isinstance(forecast, list):
        for item in forecast:
            if isinstance(item, dict) and "time" in item and "value" in item:
                try:
                    timestamp = parse_datetime_to_timestamp(item["time"])
                    value = float(item["value"])
                    forecast_series.append((timestamp, value))
                except (ValueError, TypeError):
                    continue

    return present_value, forecast_series


class DiagnosticsStateProvider:
    """Provides entity states from diagnostics inputs."""

    def __init__(self, inputs: list[dict[str, Any]]) -> None:
        """Initialize with inputs list from diagnostics."""
        self._states: dict[str, dict[str, Any]] = {}
        for entity_state in inputs:
            entity_id = entity_state.get("entity_id")
            if entity_id:
                self._states[entity_id] = entity_state

    def get(self, entity_id: str) -> dict[str, Any] | None:
        """Get entity state by ID."""
        return self._states.get(entity_id)

    def load_sensor(self, entity_id: str) -> tuple[float | None, ForecastSeries] | None:
        """Load sensor data for an entity ID."""
        state = self.get(entity_id)
        if state is None:
            return None
        return extract_forecast_from_entity(state)


def tiers_to_periods_seconds(config: Mapping[str, Any]) -> list[int]:
    """Convert tier configuration to list of period durations in seconds.

    This is a simplified version that uses fixed tier counts from config.
    """
    periods: list[int] = []
    for tier in [1, 2, 3, 4]:
        count_key = f"tier_{tier}_count"
        duration_key = f"tier_{tier}_duration"
        if count_key in config:
            count = int(config[count_key])
            duration_seconds = int(config[duration_key]) * 60
            periods.extend([duration_seconds] * count)
    return periods


def generate_forecast_timestamps(periods_seconds: Sequence[int], start_time: float) -> tuple[float, ...]:
    """Generate forecast timestamps as period boundaries."""
    timestamps: list[float] = [start_time]
    for period in periods_seconds:
        timestamps.append(timestamps[-1] + period)
    return tuple(timestamps)


def load_element_data(
    element_name: str,
    element_config: dict[str, Any],
    state_provider: DiagnosticsStateProvider,
    forecast_times: tuple[float, ...],
) -> ElementConfigData:
    """Load data for a single element from the state provider.

    Converts entity IDs to loaded numpy arrays.
    """
    element_type = element_config.get(CONF_ELEMENT_TYPE)
    if not is_element_type(element_type):
        msg = f"Unknown element type: {element_type}"
        raise ValueError(msg)

    # Get input field definitions for this element type
    adapter = ELEMENT_TYPES[element_type]
    input_fields = adapter.inputs(element_config)

    # Start with the base config
    loaded_config: dict[str, Any] = dict(element_config)
    loaded_config["name"] = element_name

    # Load each input field
    for field_name, field_info in input_fields.items():
        value = element_config.get(field_name)
        if value is None:
            continue

        # Handle constant values
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if field_info.time_series:
                if field_info.boundaries:
                    loaded_config[field_name] = np.array([float(value)] * len(forecast_times))
                else:
                    loaded_config[field_name] = np.array([float(value)] * (len(forecast_times) - 1))
            else:
                loaded_config[field_name] = float(value)
            continue

        # Handle entity IDs (string or list of strings)
        entity_ids: list[str] = []
        if isinstance(value, str):
            entity_ids = [value]
        elif isinstance(value, list):
            entity_ids = [v for v in value if isinstance(v, str)]

        if not entity_ids:
            continue

        # Load sensor data from state provider
        payloads: dict[str, tuple[float | None, ForecastSeries] | float] = {}
        for entity_id in entity_ids:
            result = state_provider.load_sensor(entity_id)
            if result is not None:
                present_value, forecast_series = result
                if forecast_series:
                    payloads[entity_id] = forecast_series
                elif present_value is not None:
                    payloads[entity_id] = present_value

        if not payloads:
            continue

        # Convert to expected format for combine_sensor_payloads
        sensor_payloads: dict[str, float | list[tuple[float, float]]] = {}
        for entity_id, payload in payloads.items():
            if isinstance(payload, float):
                sensor_payloads[entity_id] = payload
            else:
                sensor_payloads[entity_id] = list(payload)

        present_value, forecast_series = combine_sensor_payloads(sensor_payloads)

        # Fuse to horizon timestamps
        if field_info.boundaries:
            values = fuse_to_boundaries(present_value, forecast_series, list(forecast_times))
        else:
            values = fuse_to_intervals(present_value, forecast_series, list(forecast_times))

        loaded_config[field_name] = np.array(values)

    return loaded_config  # type: ignore[return-value]


def collect_model_elements(participants: Mapping[str, ElementConfigData]) -> list[ModelElementConfig]:
    """Collect and sort model elements from all participants."""
    all_model_elements: list[ModelElementConfig] = []
    for loaded_params in participants.values():
        element_type = loaded_params[CONF_ELEMENT_TYPE]
        if not is_element_type(element_type):
            continue
        model_elements = ELEMENT_TYPES[element_type].model_elements(loaded_params)
        all_model_elements.extend(model_elements)

    # Sort so connections are added last
    return sorted(
        all_model_elements,
        key=lambda e: e.get("element_type") == "connection",
    )


def create_network(
    periods_seconds: Sequence[int],
    participants: Mapping[str, ElementConfigData],
) -> Network:
    """Create a Network from configuration."""
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    net = Network(name="diag_network", periods=periods_hours)

    sorted_model_elements = collect_model_elements(participants)

    for model_element_config in sorted_model_elements:
        net.add(model_element_config)

    return net


def format_output_table(
    network: Network,
    forecast_times: tuple[float, ...],
    timezone_str: str,
) -> str:
    """Format network outputs as a table."""
    tz = ZoneInfo(timezone_str)

    # Collect outputs from elements - model layer outputs are Mapping[str, OutputData]
    outputs: dict[str, dict[str, OutputData]] = {}
    for element_name, element in network.elements.items():
        element_outputs = element.outputs()
        if element_outputs:
            outputs[element_name] = dict(element_outputs)

    # Find grid element outputs (from connection elements)
    # Grid power: positive = importing, negative = exporting
    grid_power: dict[float, float] = {}

    # Find battery element outputs
    # Battery power: positive = charging (from battery perspective), negative = discharging
    battery_power: dict[float, float] = {}
    battery_soc: dict[float, float] = {}

    # Find load and solar outputs
    load_power: dict[float, float] = {}
    solar_power: dict[float, float] = {}

    for element_name, element_outputs in outputs.items():
        for output_name, output_data in element_outputs.items():
            # Ensure we have an OutputData instance
            if not isinstance(output_data, OutputData):
                continue

            values = list(output_data.values)

            # Grid:connection - get power flow
            if element_name == "Grid:connection":
                if output_name == "connection_power_source_target":
                    # source_target = from Grid to Switchboard = import
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            grid_power[forecast_times[i]] = float(v)
                elif output_name == "connection_power_target_source":
                    # target_source = from Switchboard to Grid = export (subtract)
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            grid_power[forecast_times[i]] = grid_power.get(forecast_times[i], 0.0) - float(v)

            # Battery:normal - get battery power and SoC
            if element_name == "Battery:normal":
                if output_name == "battery_energy_stored":
                    # battery_energy_stored is in kWh, convert to SoC percentage
                    # For now, just use the raw values
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            battery_soc[forecast_times[i]] = float(v)
                elif output_name == "battery_power_charge":
                    # Charging power (positive = charging)
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            battery_power[forecast_times[i]] = battery_power.get(forecast_times[i], 0.0) + float(v)
                elif output_name == "battery_power_discharge":
                    # Discharging power (subtract to make discharge negative)
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            battery_power[forecast_times[i]] = battery_power.get(forecast_times[i], 0.0) - float(v)

            # Load:connection - get load power
            if element_name == "Load:connection" and output_name == "connection_power_target_source":
                # target_source = from Switchboard to Load = power consumed by load
                for i, v in enumerate(values):
                    if i < len(forecast_times):
                        load_power[forecast_times[i]] = float(v)

            # Solar:connection - get solar power
            if element_name == "Solar:connection" and output_name == "connection_power_source_target":
                # source_target = from Solar to Inverter = solar generation
                for i, v in enumerate(values):
                    if i < len(forecast_times):
                        solar_power[forecast_times[i]] = float(v)

    # Build table rows
    headers = ["Time", "Battery", "Grid", "Load", "Solar", "SoC"]
    rows: list[list[str]] = []

    # Get all timestamps and sort them
    all_times = sorted(set(forecast_times[:-1]))  # Exclude last boundary

    for timestamp in all_times:
        dt = datetime.fromtimestamp(timestamp, tz=tz)
        formatted_time = dt.strftime("%H:%M")

        # Get values for this timestamp
        grid = grid_power.get(timestamp, 0.0)
        battery = battery_power.get(timestamp, 0.0)
        load = load_power.get(timestamp, 0.0)
        solar = solar_power.get(timestamp, 0.0)
        soc = battery_soc.get(timestamp, 0.0)

        rows.append([
            formatted_time,
            f"{battery:.1f}",
            f"{grid:.1f}",
            f"{load:.1f}",
            f"{solar:.1f}",
            f"{soc:.1f}",
        ])

    # Format table with headers repeated every 25 rows
    result_parts: list[str] = ["\nHAEO Optimization Results"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(tabulate(chunk, headers=headers, tablefmt="simple", numalign="right", stralign="right"))
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def format_currency(value: float) -> str:
    """Format a currency value."""
    if value >= 0:
        return f"${value:.2f}"
    return f"-${abs(value):.2f}"


def get_forecast_values(outputs: dict[str, Any], entity_id: str) -> dict[str, float]:
    """Extract forecast values from an entity, keyed by time string."""
    entity = outputs.get(entity_id, {})
    attributes = entity.get("attributes", {})
    forecast = attributes.get("forecast", [])
    return {item["time"]: item["value"] for item in forecast}


def format_outputs_only_table(outputs: dict[str, Any], timezone_str: str) -> str:
    """Format pre-computed outputs from diagnostics as a table.

    This reads the already-computed outputs stored in the diagnostics file,
    without running the optimization.
    """
    # Extract forecast data for each field
    buy_prices = get_forecast_values(outputs, "number.grid_import_price")
    sell_prices = get_forecast_values(outputs, "number.grid_export_price")
    battery_power = get_forecast_values(outputs, "sensor.battery_active_power")
    grid_power = get_forecast_values(outputs, "sensor.grid_active_power")
    load_power = get_forecast_values(outputs, "sensor.load_power")
    solar_power = get_forecast_values(outputs, "sensor.solar_power")
    soc = get_forecast_values(outputs, "sensor.battery_state_of_charge")
    grid_cost_net = get_forecast_values(outputs, "sensor.grid_net_cost")

    # Get all unique times (sorted)
    all_times = sorted(set(buy_prices.keys()))

    headers = ["Time", "Buy", "Sell", "Battery", "Grid", "Load", "Solar", "SoC", "Profit"]
    rows: list[list[str]] = []

    for time_str in all_times:
        # Parse the ISO timestamp and format as HH:MM
        dt = datetime.fromisoformat(time_str)
        formatted_time = dt.strftime("%H:%M")

        # Grid power (positive = importing, negative = exporting)
        grid_net = grid_power.get(time_str, 0.0)

        # Cumulative profit = negative of cumulative cost (positive cost = spending)
        cumulative_profit = -grid_cost_net.get(time_str, 0.0)
        profit_str = format_currency(cumulative_profit)

        rows.append([
            formatted_time,
            f"{buy_prices.get(time_str, 0.0):.2f}",
            f"{sell_prices.get(time_str, 0.0):.2f}",
            f"{battery_power.get(time_str, 0.0):.1f}",
            f"{grid_net:.1f}",
            f"{load_power.get(time_str, 0.0):.1f}",
            f"{solar_power.get(time_str, 0.0):.1f}",
            f"{soc.get(time_str, 0.0):.1f}",
            profit_str,
        ])

    # Format table with headers repeated every 25 rows
    result_parts: list[str] = [f"\nHAEO Forecast (from diagnostics outputs, {timezone_str})"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(tabulate(chunk, headers=headers, tablefmt="simple", numalign="right", stralign="right"))
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def run_outputs_only(path: Path) -> None:
    """Display pre-computed outputs from a diagnostics file without running optimization."""
    # Load diagnostics
    if path.is_dir():
        print(f"Loading diagnostics from directory: {path}")
        diag = DiagnosticsData.from_split_files(path)
    else:
        print(f"Loading diagnostics from file: {path}")
        diag = DiagnosticsData.from_file(path)

    environment = diag.environment
    timezone_str = environment.get("timezone", "UTC")

    print(f"Timezone: {timezone_str}")
    print(f"Output entities: {len(diag.outputs)}")

    if not diag.outputs:
        print("Error: No outputs in diagnostics file")
        sys.exit(1)

    # Format and print results
    table = format_outputs_only_table(diag.outputs, timezone_str)
    print(table)


def run_diagnostics(path: Path) -> None:
    """Run optimization from a diagnostics file and print results."""
    # Load diagnostics
    if path.is_dir():
        print(f"Loading diagnostics from directory: {path}")
        diag = DiagnosticsData.from_split_files(path)
    else:
        print(f"Loading diagnostics from file: {path}")
        diag = DiagnosticsData.from_file(path)

    # Extract configuration
    config = diag.config
    environment = diag.environment
    participants_config = config.get("participants", {})

    # Parse timestamp and timezone
    timestamp_str = environment.get("timestamp", "")
    timezone_str = environment.get("timezone", "UTC")

    start_time = (
        parse_datetime_to_timestamp(timestamp_str)
        if timestamp_str
        else datetime.now(tz=UTC).timestamp()
    )

    print(f"Environment timestamp: {timestamp_str}")
    print(f"Timezone: {timezone_str}")
    print(f"Participants: {list(participants_config.keys())}")

    # Calculate periods from tier config
    periods_seconds = tiers_to_periods_seconds(config)
    print(f"Optimization periods: {len(periods_seconds)} intervals")

    if not periods_seconds:
        print("Error: No periods configured")
        sys.exit(1)

    # Generate forecast timestamps
    forecast_times = generate_forecast_timestamps(periods_seconds, start_time)
    print(f"Forecast horizon: {len(forecast_times)} boundaries")

    # Create state provider from inputs
    state_provider = DiagnosticsStateProvider(diag.inputs)

    # Load element data
    loaded_participants: dict[str, ElementConfigData] = {}
    for element_name, element_config in participants_config.items():
        try:
            loaded_config = load_element_data(element_name, element_config, state_provider, forecast_times)
            loaded_participants[element_name] = loaded_config
            print(f"  Loaded: {element_name} ({element_config.get(CONF_ELEMENT_TYPE)})")
        except Exception as e:
            print(f"  Warning: Failed to load {element_name}: {e}")

    if not loaded_participants:
        print("Error: No elements loaded")
        sys.exit(1)

    # Create network and run optimization
    print("\nCreating network...")
    network = create_network(periods_seconds, loaded_participants)
    print(f"Network elements: {list(network.elements.keys())}")

    print("\nRunning optimization...")
    try:
        cost = network.optimize()
        print(f"Optimization complete. Total cost: ${cost:.2f}")
    except Exception as e:
        print(f"Optimization failed: {e}")
        sys.exit(1)

    # Format and print results
    table = format_output_table(network, forecast_times, timezone_str)
    print(table)


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser(
        description="Run HAEO optimization from a diagnostics file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    uv run diag --file diagnostics.json
    uv run diag --file diagnostics.json --outputs-only
    uv run diag --file tests/scenarios/scenario_discord/
        """,
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        required=True,
        help="Path to diagnostics JSON file or directory with split files",
    )
    parser.add_argument(
        "--outputs-only",
        "-o",
        action="store_true",
        help="Skip optimization and display pre-computed outputs from diagnostics",
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    if args.outputs_only:
        run_outputs_only(args.file)
    else:
        run_diagnostics(args.file)


if __name__ == "__main__":
    main()

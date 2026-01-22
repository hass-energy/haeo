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
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.const import PERCENTAGE
from homeassistant.core import State
import numpy as np
from tabulate import tabulate

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.data.loader.extractors import extract
from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals
from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, is_element_type
from custom_components.haeo.model import Network
from custom_components.haeo.model.elements import ModelElementConfig
from custom_components.haeo.model.output_data import OutputData

type ForecastSeries = Sequence[tuple[float, float]]
type SensorPayload = float | ForecastSeries


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


class DiagnosticsStateProvider:
    """Provides entity states from diagnostics inputs using HAEO extractors."""

    def __init__(self, inputs: list[dict[str, Any]]) -> None:
        """Initialize with inputs list from diagnostics."""
        self._states: dict[str, State] = {}
        for entity_state in inputs:
            entity_id = entity_state.get("entity_id")
            if entity_id:
                # Create a mock Home Assistant State object
                state_value = str(entity_state.get("state", "unknown"))
                attributes = entity_state.get("attributes", {})
                self._states[entity_id] = State(
                    entity_id=entity_id,
                    state=state_value,
                    attributes=attributes,
                )

    def get(self, entity_id: str) -> State | None:
        """Get entity state by ID."""
        return self._states.get(entity_id)

    def load_sensor(self, entity_id: str) -> SensorPayload | None:
        """Load sensor data for an entity ID using HAEO extractors.

        Returns either a float (for simple values) or a list of (timestamp, value)
        tuples (for forecast data), or None if no data is available.
        """
        state = self.get(entity_id)
        if state is None:
            return None

        try:
            return extract(state).data
        except ValueError:
            return None


def tiers_to_periods_seconds(config: Mapping[str, Any]) -> list[int]:
    """Convert tier configuration to list of period durations in seconds."""
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


def load_sensors(
    state_provider: DiagnosticsStateProvider,
    entity_ids: Sequence[str],
) -> dict[str, SensorPayload]:
    """Load sensor data for multiple entity IDs."""
    payloads: dict[str, SensorPayload] = {}
    for entity_id in entity_ids:
        payload = state_provider.load_sensor(entity_id)
        if payload is not None:
            payloads[entity_id] = payload
    return payloads


def load_element_data(
    element_name: str,
    element_config: dict[str, Any],
    state_provider: DiagnosticsStateProvider,
    forecast_times: tuple[float, ...],
) -> ElementConfigData:
    """Load data for a single element from the state provider.

    Uses HAEO extractors to correctly parse all forecast formats (Solcast, HAEO, etc.).
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
            # Convert percentage values to ratios (0-1 range)
            unit = getattr(field_info.entity_description, "native_unit_of_measurement", None)
            converted_value = float(value) / 100.0 if unit == PERCENTAGE else float(value)

            if field_info.time_series:
                if field_info.boundaries:
                    loaded_config[field_name] = np.array([converted_value] * len(forecast_times))
                else:
                    loaded_config[field_name] = np.array([converted_value] * (len(forecast_times) - 1))
            else:
                loaded_config[field_name] = converted_value
            continue

        # Handle entity IDs (string or list of strings)
        entity_ids: list[str] = []
        if isinstance(value, str):
            entity_ids = [value]
        elif isinstance(value, list):
            entity_ids = [v for v in value if isinstance(v, str)]

        if not entity_ids:
            continue

        # Load sensor data from state provider (using extractors)
        payloads = load_sensors(state_provider, entity_ids)

        if not payloads:
            continue

        # Combine sensor payloads (handles multiple sensors, e.g. multi-string solar)
        present_value, forecast_series = combine_sensor_payloads(payloads)

        # Fuse to horizon timestamps
        if field_info.boundaries:
            values = fuse_to_boundaries(present_value, forecast_series, list(forecast_times))
        else:
            values = fuse_to_intervals(present_value, forecast_series, list(forecast_times))

        # Convert percentage values to ratios (0-1 range)
        # This matches what HaeoInputNumber.get_values() does
        unit = getattr(field_info.entity_description, "native_unit_of_measurement", None)
        if unit == PERCENTAGE:
            values = [v / 100.0 for v in values]

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


def format_currency(value: float) -> str:
    """Format a currency value."""
    if value >= 0:
        return f"${value:.2f}"
    return f"-${abs(value):.2f}"


def get_forecast_values(outputs: dict[str, Any], entity_id: str) -> dict[str, float]:
    """Extract forecast values from a diagnostics output entity, keyed by time string."""
    entity = outputs.get(entity_id, {})
    attributes = entity.get("attributes", {})
    forecast = attributes.get("forecast", [])
    return {item["time"]: item["value"] for item in forecast}


def format_output_table_from_diagnostics(outputs: dict[str, Any], timezone_str: str) -> str:
    """Format pre-computed outputs from diagnostics as a table.

    This reads the already-computed outputs stored in the diagnostics file.
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
    result_parts: list[str] = [f"\nHAEO Forecast ({timezone_str})"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(tabulate(chunk, headers=headers, tablefmt="simple", numalign="right", stralign="right"))
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def format_output_table_from_network(
    network: Network,
    loaded_participants: dict[str, ElementConfigData],
    forecast_times: tuple[float, ...],
    timezone_str: str,
) -> str:
    """Format network outputs as a table after running optimization.

    Uses the adapter layer's outputs() methods to transform model outputs
    into the same format as the diagnostics outputs.
    """
    tz = ZoneInfo(timezone_str)

    # Collect raw model outputs from all network elements
    model_outputs: dict[str, Any] = {
        element_name: element.outputs() for element_name, element in network.elements.items()
    }

    # Process outputs through each element's adapter
    # This transforms raw model outputs into sensor-friendly formats
    adapter_outputs: dict[str, dict[str, OutputData]] = {}

    for element_name, element_config in loaded_participants.items():
        element_type = element_config.get(CONF_ELEMENT_TYPE)
        if not is_element_type(element_type):
            continue

        adapter = ELEMENT_TYPES[element_type]
        try:
            # Call the adapter's outputs method
            element_outputs = adapter.outputs(
                name=element_name,
                model_outputs=model_outputs,
                config=element_config,
                periods=network.periods,
            )
            # Flatten device outputs: {device_name: {output_name: OutputData}}
            for device_name, device_outputs in element_outputs.items():
                adapter_outputs[f"{element_name}:{device_name}"] = dict(device_outputs)
        except Exception as e:
            print(f"  Warning: Failed to get outputs for {element_name}: {e}")

    # Extract prices from Grid config (these are inputs, not outputs)
    grid_import_price_array: np.ndarray | None = None
    grid_export_price_array: np.ndarray | None = None
    for element_config in loaded_participants.values():
        if element_config.get(CONF_ELEMENT_TYPE) == "grid":
            import_price = element_config.get("import_price")
            export_price = element_config.get("export_price")
            if isinstance(import_price, np.ndarray):
                grid_import_price_array = import_price
            if isinstance(export_price, np.ndarray):
                grid_export_price_array = export_price
            break

    # Extract data from adapter outputs
    grid_power: dict[float, float] = {}
    battery_power: dict[float, float] = {}
    battery_soc: dict[float, float] = {}
    load_power: dict[float, float] = {}
    solar_power: dict[float, float] = {}
    grid_import_price: dict[float, float] = {}
    grid_export_price: dict[float, float] = {}
    grid_cost_cumulative: dict[float, float] = {}

    # Populate prices from config arrays
    n_intervals = len(forecast_times) - 1
    if grid_import_price_array is not None:
        for i in range(min(len(grid_import_price_array), n_intervals)):
            grid_import_price[forecast_times[i]] = float(grid_import_price_array[i])
    if grid_export_price_array is not None:
        for i in range(min(len(grid_export_price_array), n_intervals)):
            grid_export_price[forecast_times[i]] = float(grid_export_price_array[i])

    for full_name, element_outputs in adapter_outputs.items():
        for output_name, output_data in element_outputs.items():
            if not isinstance(output_data, OutputData):
                continue

            values = list(output_data.values)

            # Grid outputs (from Grid:grid device)
            if "Grid:grid" in full_name:
                if output_name == "grid_power_active":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            grid_power[forecast_times[i]] = float(v)
                elif output_name == "grid_cost_net":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            grid_cost_cumulative[forecast_times[i]] = float(v)

            # Battery outputs (from Battery:battery device)
            if "Battery:battery" in full_name:
                if output_name == "battery_state_of_charge":
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            # SoC is a ratio (0-1), convert to percentage
                            battery_soc[forecast_times[i]] = float(v) * 100.0
                elif output_name == "battery_power_active":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            battery_power[forecast_times[i]] = float(v)

            # Load outputs (from Load:load device)
            if "Load:load" in full_name and output_name == "load_power":
                for i, v in enumerate(values):
                    if i < len(forecast_times) - 1:
                        load_power[forecast_times[i]] = float(v)

            # Solar outputs (from Solar:solar device)
            if "Solar:solar" in full_name and output_name == "solar_power":
                for i, v in enumerate(values):
                    if i < len(forecast_times) - 1:
                        solar_power[forecast_times[i]] = float(v)

    # Build table rows
    headers = ["Time", "Buy", "Sell", "Battery", "Grid", "Load", "Solar", "SoC", "Profit"]
    rows: list[list[str]] = []

    all_times = sorted(set(forecast_times[:-1]))  # Exclude last boundary

    for timestamp in all_times:
        dt = datetime.fromtimestamp(timestamp, tz=tz)
        formatted_time = dt.strftime("%H:%M")

        # Cumulative profit = negative of cumulative cost
        cumulative_profit = -grid_cost_cumulative.get(timestamp, 0.0)
        profit_str = format_currency(cumulative_profit)

        rows.append([
            formatted_time,
            f"{grid_import_price.get(timestamp, 0.0):.2f}",
            f"{grid_export_price.get(timestamp, 0.0):.2f}",
            f"{battery_power.get(timestamp, 0.0):.1f}",
            f"{grid_power.get(timestamp, 0.0):.1f}",
            f"{load_power.get(timestamp, 0.0):.1f}",
            f"{solar_power.get(timestamp, 0.0):.1f}",
            f"{battery_soc.get(timestamp, 0.0):.1f}",
            profit_str,
        ])

    # Format table with headers repeated every 25 rows
    result_parts: list[str] = [f"\nHAEO Optimization Results ({timezone_str})"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(tabulate(chunk, headers=headers, tablefmt="simple", numalign="right", stralign="right"))
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def run_diagnostics(path: Path, *, outputs_only: bool = False) -> None:
    """Run diagnostics processing from a file.

    Args:
        path: Path to diagnostics JSON file or directory with split files
        outputs_only: If True, skip optimization and display pre-computed outputs

    """
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

    # If outputs-only, just display pre-computed outputs
    if outputs_only:
        if not diag.outputs:
            print("Error: No outputs in diagnostics file")
            sys.exit(1)

        print(f"Output entities: {len(diag.outputs)}")
        table = format_output_table_from_diagnostics(diag.outputs, timezone_str)
        print(table)
        return

    # Calculate periods from tier config
    periods_seconds = tiers_to_periods_seconds(config)
    print(f"Optimization periods: {len(periods_seconds)} intervals")

    if not periods_seconds:
        print("Error: No periods configured")
        sys.exit(1)

    # Use forecast_timestamps from environment if available (for exact reproducibility)
    # Otherwise fall back to generating from config (backward compatibility)
    if "forecast_timestamps" in environment:
        forecast_times = tuple(environment["forecast_timestamps"])
        print(f"Forecast horizon: {len(forecast_times)} boundaries (from diagnostics)")
    else:
        forecast_times = generate_forecast_timestamps(periods_seconds, start_time)
        print(f"Forecast horizon: {len(forecast_times)} boundaries (generated)")

    # Create state provider from inputs (uses HAEO extractors)
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
    table = format_output_table_from_network(network, loaded_participants, forecast_times, timezone_str)
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

    run_diagnostics(args.file, outputs_only=args.outputs_only)


if __name__ == "__main__":
    main()

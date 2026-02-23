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
from collections.abc import Sequence
import contextlib
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import PERCENTAGE
from homeassistant.core import State
import numpy as np
from tabulate import tabulate

from custom_components.haeo.const import CONF_ELEMENT_TYPE
from custom_components.haeo.coordinator.network import collect_model_elements
from custom_components.haeo.core.model import Network
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema.sections import SECTION_COMMON, SECTION_PRICING
from custom_components.haeo.data.loader.extractors import extract
from custom_components.haeo.data.loader.extractors.utils.parse_datetime import parse_datetime_to_timestamp
from custom_components.haeo.data.util.forecast_combiner import combine_sensor_payloads
from custom_components.haeo.data.util.forecast_fuser import fuse_to_boundaries, fuse_to_intervals
from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, get_input_fields, is_element_type
from custom_components.haeo.migrations.v1_3 import migrate_subentry_data
from custom_components.haeo.schema.constant_value import is_constant_value
from custom_components.haeo.schema.entity_value import is_entity_value
from custom_components.haeo.schema.none_value import is_none_value
from custom_components.haeo.util.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds

type ForecastSeries = Sequence[tuple[float, float]]
type SensorPayload = float | ForecastSeries

MIN_INTERVAL_POINTS = 2


@dataclass
class RowData:
    """Data for a single table row."""

    time: str  # Formatted time string (HH:MM)
    timestamp: float  # Unix timestamp for matching rows
    buy: float
    sell: float
    battery: float
    grid: float
    load: float
    solar: float
    soc: float
    profit: float


@dataclass
class DiagnosticsData:
    """Parsed diagnostics data."""

    config: dict[str, Any]
    environment: dict[str, Any]
    info: dict[str, Any]
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
            info=data.get("info", {}),
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", {}),
        )

    @classmethod
    def from_split_files(cls, directory: Path) -> DiagnosticsData:
        """Load diagnostics from split JSON files (config.json, environment.json, etc.)."""
        config_file = directory / "config.json"
        environment_file = directory / "environment.json"
        info_file = directory / "info.json"
        inputs_file = directory / "inputs.json"
        outputs_file = directory / "outputs.json"

        with config_file.open() as f:
            config = json.load(f)
        with environment_file.open() as f:
            environment = json.load(f)
        with inputs_file.open() as f:
            inputs = json.load(f)

        info: dict[str, Any] = {}
        if info_file.exists():
            with info_file.open() as f:
                info = json.load(f)

        outputs: dict[str, Any] = {}
        if outputs_file.exists():
            with outputs_file.open() as f:
                outputs = json.load(f)

        return cls(config=config, environment=environment, info=info, inputs=inputs, outputs=outputs)


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


def _needs_subentry_migration(element_config: dict[str, Any]) -> bool:
    """Return True when a participant config looks legacy or mixed."""
    if SECTION_COMMON not in element_config:
        return True

    for key, value in element_config.items():
        if key == CONF_ELEMENT_TYPE:
            continue
        # Sectioned configs should store section payloads as dictionaries.
        if not isinstance(value, dict):
            return True

    return False


def normalize_participant_config_for_diag(element_name: str, element_config: dict[str, Any]) -> dict[str, Any]:
    """Normalize a participant config to sectioned format for diagnostics CLI."""
    if not _needs_subentry_migration(element_config):
        return element_config

    subentry = ConfigSubentry(
        data=MappingProxyType(element_config),
        subentry_type=element_config.get(CONF_ELEMENT_TYPE, ""),
        title=element_name,
        unique_id=None,
    )
    migrated = migrate_subentry_data(subentry)
    return migrated if migrated is not None else element_config


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

    input_fields = get_input_fields(element_config)

    # Start with a shallow copy and clone nested section dictionaries so we can
    # safely mutate loaded values without mutating the original input config.
    loaded_config: dict[str, Any] = {
        key: dict(value) if isinstance(value, dict) else value for key, value in element_config.items()
    }
    loaded_config.setdefault(SECTION_COMMON, {})["name"] = element_name

    # Load each input field (nested: section → field → InputFieldInfo)
    for section_name, section_fields in input_fields.items():
        section_config = element_config.get(section_name)
        if not isinstance(section_config, dict):
            continue

        for field_name, field_info in section_fields.items():
            value = section_config.get(field_name)
            if value is None:
                continue

            # Unwrap structured schema values ({"type": "entity/constant/none", "value": ...})
            if is_none_value(value):
                loaded_section = loaded_config.get(section_name)
                if isinstance(loaded_section, dict):
                    loaded_section.pop(field_name, None)
                continue
            if is_constant_value(value) or is_entity_value(value):
                value = value["value"]

            # Handle boolean constants (store directly, no conversion needed)
            if isinstance(value, bool):
                loaded_config.setdefault(section_name, {})[field_name] = value
                continue

            # Handle numeric constant values
            if isinstance(value, (int, float)):
                # Convert percentage values to ratios (0-1 range)
                unit = getattr(field_info.entity_description, "native_unit_of_measurement", None)
                converted_value = float(value) / 100.0 if unit == PERCENTAGE else float(value)

                if field_info.time_series:
                    if field_info.boundaries:
                        loaded_config.setdefault(section_name, {})[field_name] = np.array(
                            [converted_value] * len(forecast_times)
                        )
                    else:
                        loaded_config.setdefault(section_name, {})[field_name] = np.array(
                            [converted_value] * (len(forecast_times) - 1)
                        )
                else:
                    loaded_config.setdefault(section_name, {})[field_name] = converted_value
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

            # Convert percentage values to ratios (0-1 range)
            # This matches what HaeoInputNumber.get_values() does
            unit = getattr(field_info.entity_description, "native_unit_of_measurement", None)

            if not field_info.time_series:
                # Scalar field: use present value directly
                scalar = present_value if present_value is not None else 0.0
                if unit == PERCENTAGE:
                    scalar /= 100.0
                loaded_config.setdefault(section_name, {})[field_name] = scalar
            else:
                # Time series: fuse to horizon timestamps
                if field_info.boundaries:
                    values = fuse_to_boundaries(present_value, forecast_series, list(forecast_times))
                else:
                    values = fuse_to_intervals(present_value, forecast_series, list(forecast_times))

                if unit == PERCENTAGE:
                    values = [v / 100.0 for v in values]

                loaded_config.setdefault(section_name, {})[field_name] = np.array(values)

    return loaded_config  # type: ignore[return-value]


def format_currency(value: float) -> str:
    """Format a currency value."""
    if value >= 0:
        return f"${value:.2f}"
    return f"-${abs(value):.2f}"


def find_output_entity(outputs: dict[str, Any], element_name: str, field_or_output_name: str) -> dict[str, Any] | None:
    """Find an output entity by element_name and field_name or output_name attributes.

    Number entities (inputs) have field_name attribute:
        {"element_name": "Grid", "field_name": "export_price", "forecast": [...]}

    Sensor entities (outputs) have output_name attribute:
        {"element_name": "Battery", "output_name": "battery_state_of_charge", "forecast": [...]}

    Args:
        outputs: Dictionary of output entities from diagnostics
        element_name: The element name (e.g., "Grid", "Battery")
        field_or_output_name: The field_name or output_name to match

    Returns:
        The entity dict if found, None otherwise.

    """
    for entity in outputs.values():
        attrs = entity.get("attributes", {})
        if attrs.get("element_name") != element_name:
            continue
        # Check field_name (for number.* entities)
        if attrs.get("field_name") == field_or_output_name:
            return entity
        # Check output_name (for sensor.* entities)
        if attrs.get("output_name") == field_or_output_name:
            return entity
    return None


def get_forecast_by_field(outputs: dict[str, Any], element_name: str, field_or_output_name: str) -> dict[str, float]:
    """Extract forecast values by element_name and field/output name, keyed by time string."""
    entity = find_output_entity(outputs, element_name, field_or_output_name)
    if entity is None:
        return {}
    forecast = entity.get("attributes", {}).get("forecast", [])
    return {item["time"]: item["value"] for item in forecast}


def get_forecast_by_fields(
    outputs: dict[str, Any],
    element_name: str,
    field_or_output_names: Sequence[str],
) -> dict[str, float]:
    """Extract forecast values using multiple field/output aliases, in order."""
    for field_or_output_name in field_or_output_names:
        values = get_forecast_by_field(outputs, element_name, field_or_output_name)
        if values:
            return values
    return {}


def infer_interval_starts_from_outputs(outputs: dict[str, Any], config: dict[str, Any]) -> list[float]:
    """Infer interval start timestamps from diagnostics outputs."""
    participants = config.get("participants", {})
    grid_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "grid"), "Grid")
    battery_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "battery"), "Battery")
    load_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "load"), "Load")
    solar_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "solar"), "Solar")

    candidates = (
        get_forecast_by_field(outputs, grid_name, "grid_power_active"),
        get_forecast_by_field(outputs, grid_name, "grid_cost_net"),
        get_forecast_by_fields(outputs, grid_name, ("price_source_target", "import_price")),
        get_forecast_by_field(outputs, battery_name, "battery_power_active"),
        get_forecast_by_field(outputs, load_name, "load_power"),
        get_forecast_by_field(outputs, solar_name, "solar_power"),
    )

    for series in candidates:
        if len(series) < MIN_INTERVAL_POINTS:
            continue
        timestamps = sorted(parse_datetime_to_timestamp(time_str) for time_str in series)
        if len(timestamps) >= MIN_INTERVAL_POINTS:
            return [float(timestamp) for timestamp in timestamps]
    return []


def get_forecast_values(outputs: dict[str, Any], entity_id: str) -> dict[str, float]:
    """Extract forecast values from a diagnostics output entity by entity_id.

    Falls back to exact entity_id match for backward compatibility.
    """
    entity = outputs.get(entity_id, {})
    attributes = entity.get("attributes", {})
    forecast = attributes.get("forecast", [])
    return {item["time"]: item["value"] for item in forecast}


def format_output_table_from_diagnostics(outputs: dict[str, Any], timezone_str: str, config: dict[str, Any]) -> str:
    """Format pre-computed outputs from diagnostics as a table.

    This reads the already-computed outputs stored in the diagnostics file.
    Uses element names from config to find output entities by their attributes.
    """
    # Find element names from config
    participants = config.get("participants", {})
    grid_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "grid"), "Grid")
    battery_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "battery"), "Battery")
    load_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "load"), "Load")
    solar_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "solar"), "Solar")

    # Extract forecast data using element_name and field_name/output_name attributes
    # Prices use field_name (number.* entities), sensors use output_name (sensor.* entities)
    buy_prices = get_forecast_by_fields(outputs, grid_name, ("price_source_target", "import_price"))
    sell_prices = get_forecast_by_fields(outputs, grid_name, ("price_target_source", "export_price"))
    battery_power = get_forecast_by_field(outputs, battery_name, "battery_power_active")
    grid_power = get_forecast_by_field(outputs, grid_name, "grid_power_active")
    load_power = get_forecast_by_field(outputs, load_name, "load_power")
    solar_power = get_forecast_by_field(outputs, solar_name, "solar_power")
    soc = get_forecast_by_field(outputs, battery_name, "battery_state_of_charge")
    grid_cost_net = get_forecast_by_field(outputs, grid_name, "grid_cost_net")

    # Get all unique times from any available series (sorted)
    all_times = sorted(set(buy_prices.keys()) | set(grid_power.keys()) | set(battery_power.keys()) | set(soc.keys()))

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

        rows.append(
            [
                formatted_time,
                f"{buy_prices.get(time_str, 0.0):.4f}",
                f"{sell_prices.get(time_str, 0.0):.4f}",
                f"{battery_power.get(time_str, 0.0):.1f}",
                f"{grid_net:.1f}",
                f"{load_power.get(time_str, 0.0):.1f}",
                f"{solar_power.get(time_str, 0.0):.1f}",
                f"{soc.get(time_str, 0.0):.1f}",
                profit_str,
            ]
        )

    # Format table with headers repeated every 25 rows
    result_parts: list[str] = [f"\nHAEO Forecast ({timezone_str})"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(
            tabulate(
                chunk,
                headers=headers,
                tablefmt="simple",
                numalign="right",
                stralign="right",
                disable_numparse=True,
            )
        )
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

    # Extract prices from Grid config (sectioned: pricing.price_source_target/price_target_source)
    grid_import_price_array: np.ndarray | None = None
    grid_export_price_array: np.ndarray | None = None
    for element_config in loaded_participants.values():
        if element_config.get(CONF_ELEMENT_TYPE) == "grid":
            pricing = element_config.get(SECTION_PRICING, {})
            import_price = pricing.get("price_source_target")
            export_price = pricing.get("price_target_source")
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

        rows.append(
            [
                formatted_time,
                f"{grid_import_price.get(timestamp, 0.0):.4f}",
                f"{grid_export_price.get(timestamp, 0.0):.4f}",
                f"{battery_power.get(timestamp, 0.0):.1f}",
                f"{grid_power.get(timestamp, 0.0):.1f}",
                f"{load_power.get(timestamp, 0.0):.1f}",
                f"{solar_power.get(timestamp, 0.0):.1f}",
                f"{battery_soc.get(timestamp, 0.0):.1f}",
                profit_str,
            ]
        )

    # Format table with headers repeated every 25 rows
    result_parts: list[str] = [f"\nHAEO Optimization Results ({timezone_str})"]
    chunk_size = 25
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(
            tabulate(
                chunk,
                headers=headers,
                tablefmt="simple",
                numalign="right",
                stralign="right",
                disable_numparse=True,
            )
        )
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def extract_rows_from_diagnostics(outputs: dict[str, Any], _timezone_str: str, config: dict[str, Any]) -> list[RowData]:
    """Extract row data from pre-computed diagnostics outputs."""
    # Find element names from config
    participants = config.get("participants", {})
    grid_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "grid"), "Grid")
    battery_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "battery"), "Battery")
    load_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "load"), "Load")
    solar_name = next((name for name, cfg in participants.items() if cfg.get("element_type") == "solar"), "Solar")

    # Extract forecast data using element_name and field_name/output_name attributes
    # Prices use field_name (number.* entities), sensors use output_name (sensor.* entities)
    buy_prices = get_forecast_by_fields(outputs, grid_name, ("price_source_target", "import_price"))
    sell_prices = get_forecast_by_fields(outputs, grid_name, ("price_target_source", "export_price"))
    battery_power = get_forecast_by_field(outputs, battery_name, "battery_power_active")
    grid_power = get_forecast_by_field(outputs, grid_name, "grid_power_active")
    load_power = get_forecast_by_field(outputs, load_name, "load_power")
    solar_power = get_forecast_by_field(outputs, solar_name, "solar_power")
    soc = get_forecast_by_field(outputs, battery_name, "battery_state_of_charge")
    grid_cost_net = get_forecast_by_field(outputs, grid_name, "grid_cost_net")

    # Get all unique times from any available series (sorted)
    all_times = sorted(set(buy_prices.keys()) | set(grid_power.keys()) | set(battery_power.keys()) | set(soc.keys()))

    rows: list[RowData] = []
    for time_str in all_times:
        dt = datetime.fromisoformat(time_str)
        formatted_time = dt.strftime("%H:%M")
        timestamp = dt.timestamp()

        # Use +0.0 to convert -0.0 to 0.0 for consistent display
        rows.append(
            RowData(
                time=formatted_time,
                timestamp=timestamp,
                buy=buy_prices.get(time_str, 0.0) + 0.0,
                sell=sell_prices.get(time_str, 0.0) + 0.0,
                battery=battery_power.get(time_str, 0.0) + 0.0,
                grid=grid_power.get(time_str, 0.0) + 0.0,
                load=load_power.get(time_str, 0.0) + 0.0,
                solar=solar_power.get(time_str, 0.0) + 0.0,
                soc=soc.get(time_str, 0.0) + 0.0,
                profit=-grid_cost_net.get(time_str, 0.0) + 0.0,
            )
        )

    return rows


def extract_rows_from_network(
    network: Network,
    loaded_participants: dict[str, ElementConfigData],
    forecast_times: tuple[float, ...],
    timezone_str: str,
) -> list[RowData]:
    """Extract row data from network optimization results."""
    tz = ZoneInfo(timezone_str)

    # Collect raw model outputs from all network elements
    model_outputs: dict[str, Any] = {
        element_name: element.outputs() for element_name, element in network.elements.items()
    }

    # Process outputs through each element's adapter
    adapter_outputs: dict[str, dict[str, OutputData]] = {}

    for element_name, element_config in loaded_participants.items():
        element_type = element_config.get(CONF_ELEMENT_TYPE)
        if not is_element_type(element_type):
            continue

        adapter = ELEMENT_TYPES[element_type]
        with contextlib.suppress(Exception):
            element_outputs = adapter.outputs(
                name=element_name,
                model_outputs=model_outputs,
                config=element_config,
                periods=network.periods,
            )
            for device_name, device_outputs in element_outputs.items():
                adapter_outputs[f"{element_name}:{device_name}"] = dict(device_outputs)

    # Extract prices from Grid config (sectioned: pricing.price_source_target/price_target_source)
    grid_import_price_array: np.ndarray | None = None
    grid_export_price_array: np.ndarray | None = None
    for element_config in loaded_participants.values():
        if element_config.get(CONF_ELEMENT_TYPE) == "grid":
            pricing = element_config.get(SECTION_PRICING, {})
            import_price = pricing.get("price_source_target")
            export_price = pricing.get("price_target_source")
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

    n_intervals = len(forecast_times) - 1
    if grid_import_price_array is not None:
        for i in range(min(len(grid_import_price_array), n_intervals)):
            grid_import_price[forecast_times[i]] = float(grid_import_price_array[i])
    if grid_export_price_array is not None:
        for i in range(min(len(grid_export_price_array), n_intervals)):
            grid_export_price[forecast_times[i]] = float(grid_export_price_array[i])

    for full_name, element_outputs in adapter_outputs.items():
        for output_name, output_data in element_outputs.items():
            values = list(output_data.values)

            if "Grid:grid" in full_name:
                if output_name == "grid_power_active":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            grid_power[forecast_times[i]] = float(v)
                elif output_name == "grid_cost_net":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            grid_cost_cumulative[forecast_times[i]] = float(v)

            if "Battery:battery" in full_name:
                if output_name == "battery_state_of_charge":
                    for i, v in enumerate(values):
                        if i < len(forecast_times):
                            battery_soc[forecast_times[i]] = float(v) * 100.0
                elif output_name == "battery_power_active":
                    for i, v in enumerate(values):
                        if i < len(forecast_times) - 1:
                            battery_power[forecast_times[i]] = float(v)

            if "Load:load" in full_name and output_name == "load_power":
                for i, v in enumerate(values):
                    if i < len(forecast_times) - 1:
                        load_power[forecast_times[i]] = float(v)

            if "Solar:solar" in full_name and output_name == "solar_power":
                for i, v in enumerate(values):
                    if i < len(forecast_times) - 1:
                        solar_power[forecast_times[i]] = float(v)

    # Build row data (no rounding - diagnostics stores unrounded values)
    rows: list[RowData] = []
    all_times = sorted(set(forecast_times[:-1]))

    for timestamp in all_times:
        dt = datetime.fromtimestamp(timestamp, tz=tz)
        formatted_time = dt.strftime("%H:%M")

        # Use +0.0 to convert -0.0 to 0.0
        rows.append(
            RowData(
                time=formatted_time,
                timestamp=timestamp,
                buy=grid_import_price.get(timestamp, 0.0) + 0.0,
                sell=grid_export_price.get(timestamp, 0.0) + 0.0,
                battery=battery_power.get(timestamp, 0.0) + 0.0,
                grid=grid_power.get(timestamp, 0.0) + 0.0,
                load=load_power.get(timestamp, 0.0) + 0.0,
                solar=solar_power.get(timestamp, 0.0) + 0.0,
                soc=battery_soc.get(timestamp, 0.0) + 0.0,
                profit=-grid_cost_cumulative.get(timestamp, 0.0) + 0.0,
            )
        )

    return rows


def format_comparison_table(
    diag_rows: list[RowData],
    rerun_rows: list[RowData],
    timezone_str: str,
) -> str:
    """Format a comparison table showing diagnostics vs rerun values.

    Shows both values side-by-side with rerun values highlighted (inverted) when different.
    """
    # ANSI escape codes for inverted text
    ansi_invert = "\033[7m"
    ansi_reset = "\033[0m"

    def highlight_if_diff(diag_str: str, rerun_str: str, *, comparable: bool) -> str:
        """Highlight rerun value if its formatted string differs from diagnostics."""
        if comparable and diag_str != rerun_str:
            return f"{ansi_invert}{rerun_str}{ansi_reset}"
        return rerun_str

    def fmt_2(value: float | None) -> str:
        return f"{value:.2f}" if value is not None else "N/A"

    def fmt_1(value: float | None) -> str:
        return f"{value:.1f}" if value is not None else "N/A"

    def fmt_currency(value: float | None) -> str:
        return format_currency(value) if value is not None else "N/A"

    # Match rows by timestamp
    diag_by_ts = {r.timestamp: r for r in diag_rows}
    rerun_by_ts = {r.timestamp: r for r in rerun_rows}

    all_timestamps = sorted(set(diag_by_ts.keys()) | set(rerun_by_ts.keys()))

    # Headers: Time, then for each field: Diag | Rerun
    headers = [
        "Time",
        "Buy(D)",
        "Buy(R)",
        "Sell(D)",
        "Sell(R)",
        "Batt(D)",
        "Batt(R)",
        "Grid(D)",
        "Grid(R)",
        "SoC(D)",
        "SoC(R)",
        "Profit(D)",
        "Profit(R)",
    ]

    rows: list[list[str]] = []
    total_diffs = {"battery": 0.0, "grid": 0.0, "soc": 0.0, "profit": 0.0}
    overlap_count = 0

    for ts in all_timestamps:
        d = diag_by_ts.get(ts)
        r = rerun_by_ts.get(ts)

        time_str = d.time if d else (r.time if r else "??:??")
        is_overlap = d is not None and r is not None

        # Get values or defaults
        d_buy = d.buy if d else None
        d_sell = d.sell if d else None
        d_battery = d.battery if d else None
        d_grid = d.grid if d else None
        d_soc = d.soc if d else None
        d_profit = d.profit if d else None

        r_buy = r.buy if r else None
        r_sell = r.sell if r else None
        r_battery = r.battery if r else None
        r_grid = r.grid if r else None
        r_soc = r.soc if r else None
        r_profit = r.profit if r else None

        # Track totals for summary using only overlapping rows.
        if d is not None and r is not None:
            total_diffs["battery"] += abs(r.battery - d.battery)
            total_diffs["grid"] += abs(r.grid - d.grid)
            total_diffs["soc"] += abs(r.soc - d.soc)
            total_diffs["profit"] += abs(r.profit - d.profit)
            overlap_count += 1

        # Format values
        d_buy_str = fmt_2(d_buy)
        r_buy_str = fmt_2(r_buy)
        d_sell_str = fmt_2(d_sell)
        r_sell_str = fmt_2(r_sell)
        d_batt_str = fmt_1(d_battery)
        r_batt_str = fmt_1(r_battery)
        d_grid_str = fmt_1(d_grid)
        r_grid_str = fmt_1(r_grid)
        d_soc_str = fmt_1(d_soc)
        r_soc_str = fmt_1(r_soc)
        d_profit_str = fmt_currency(d_profit)
        r_profit_str = fmt_currency(r_profit)

        # Build row, highlighting rerun values if different
        rows.append(
            [
                time_str,
                d_buy_str,
                highlight_if_diff(d_buy_str, r_buy_str, comparable=is_overlap),
                d_sell_str,
                highlight_if_diff(d_sell_str, r_sell_str, comparable=is_overlap),
                d_batt_str,
                highlight_if_diff(d_batt_str, r_batt_str, comparable=is_overlap),
                d_grid_str,
                highlight_if_diff(d_grid_str, r_grid_str, comparable=is_overlap),
                d_soc_str,
                highlight_if_diff(d_soc_str, r_soc_str, comparable=is_overlap),
                d_profit_str,
                highlight_if_diff(d_profit_str, r_profit_str, comparable=is_overlap),
            ]
        )

    # Summary
    avg_diffs = {k: v / overlap_count if overlap_count > 0 else 0.0 for k, v in total_diffs.items()}

    result_parts: list[str] = [
        f"\nHAEO Comparison: Diagnostics (D) vs Rerun (R) [{timezone_str}]",
        f"Rows compared: {overlap_count} overlap / {len(rows)} total",
        f"Mean absolute differences: Battery={avg_diffs['battery']:.2f}kW, "
        f"Grid={avg_diffs['grid']:.2f}kW, SoC={avg_diffs['soc']:.2f}%, "
        f"Profit=${avg_diffs['profit']:.3f}",
        "",
    ]

    # Format table with headers repeated every 20 rows
    chunk_size = 20
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        result_parts.append(
            tabulate(
                chunk,
                headers=headers,
                tablefmt="simple",
                numalign="right",
                stralign="right",
                disable_numparse=True,
            )
        )
        if i + chunk_size < len(rows):
            result_parts.append("")

    return "\n".join(result_parts)


def run_diagnostics(
    path: Path,
    *,
    outputs_only: bool = False,
    compare: bool = False,
    preset: str | None = None,
) -> None:
    """Run diagnostics processing from a file.

    Args:
        path: Path to diagnostics JSON file or directory with split files
        outputs_only: If True, skip optimization and display pre-computed outputs
        preset: Override horizon preset for tier alignment
        compare: If True, show comparison table of diagnostics vs rerun outputs

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

    start_time = parse_datetime_to_timestamp(timestamp_str) if timestamp_str else datetime.now(tz=UTC).timestamp()

    print(f"Environment timestamp: {timestamp_str}")
    print(f"Timezone: {timezone_str}")
    print(f"Participants: {list(participants_config.keys())}")

    # If outputs-only (without compare), just display pre-computed outputs
    if outputs_only and not compare:
        if not diag.outputs:
            print("Error: No outputs in diagnostics file")
            sys.exit(1)

        print(f"Output entities: {len(diag.outputs)}")
        table = format_output_table_from_diagnostics(diag.outputs, timezone_str, config)
        print(table)
        return

    # Determine the optimization start time for tier alignment.
    # Priority: info.horizon_start > inferred from outputs > environment timestamp > now
    horizon_start_str = diag.info.get("horizon_start")
    if horizon_start_str:
        start_dt = datetime.fromisoformat(horizon_start_str)
        print(f"Horizon start: {horizon_start_str}")
    else:
        # Try to infer start time from output forecast timestamps
        start_dt = None
        if diag.outputs:
            for entity in diag.outputs.values():
                forecast = entity.get("attributes", {}).get("forecast", [])
                if forecast and "time" in forecast[0]:
                    first_time_str = forecast[0]["time"]
                    start_dt = datetime.fromisoformat(first_time_str)
                    print(f"Inferred start time from outputs: {first_time_str}")
                    break
        if start_dt is None:
            start_dt = datetime.fromisoformat(timestamp_str) if timestamp_str else None

    # Build forecast timeline.
    # Priority:
    # 1) environment.forecast_timestamps for exact reproducibility,
    # 2) in compare mode, infer interval starts from diagnostics outputs,
    # 3) otherwise generate from tier config.
    periods_seconds: list[int] = []
    forecast_times: tuple[float, ...] = ()

    if "forecast_timestamps" in environment:
        forecast_times = tuple(environment["forecast_timestamps"])
        # Derive periods_seconds from the actual forecast timestamps
        periods_seconds = [int(forecast_times[i + 1] - forecast_times[i]) for i in range(len(forecast_times) - 1)]
        print(f"Optimization periods: {len(periods_seconds)} intervals (from diagnostics)")
        print(f"Forecast horizon: {len(forecast_times)} boundaries (from diagnostics)")
    elif compare and diag.outputs:
        interval_starts = infer_interval_starts_from_outputs(diag.outputs, config)
        if len(interval_starts) >= MIN_INTERVAL_POINTS:
            periods_seconds = [
                round(interval_starts[i + 1] - interval_starts[i]) for i in range(len(interval_starts) - 1)
            ]
            if periods_seconds and all(period > 0 for period in periods_seconds):
                # Interval-start series has n starts for n intervals; append the last step.
                last_step = periods_seconds[-1]
                periods_seconds.append(last_step)
                forecast_times = (*interval_starts, interval_starts[-1] + last_step)
                print(f"Optimization periods: {len(periods_seconds)} intervals (from diagnostics outputs)")
                print(f"Forecast horizon: {len(forecast_times)} boundaries (from diagnostics outputs)")
                if preset:
                    print("Ignoring preset override in compare mode to preserve diagnostics alignment")
            else:
                interval_starts = []
        if len(interval_starts) < MIN_INTERVAL_POINTS:
            print("Warning: Could not infer output-aligned timeline, falling back to config tiers")
            # Apply preset override if provided via CLI
            effective_config = dict(config)
            if preset:
                effective_config["horizon_preset"] = preset
                print(f"Using preset override: {preset}")
            periods_seconds = tiers_to_periods_seconds(effective_config, start_time=start_dt)
            print(f"Optimization periods: {len(periods_seconds)} intervals (from config)")

            if not periods_seconds:
                print("Error: No periods configured")
                sys.exit(1)

            effective_start = start_dt.timestamp() if start_dt else start_time
            forecast_times = generate_forecast_timestamps(periods_seconds, effective_start)
            print(f"Forecast horizon: {len(forecast_times)} boundaries (generated)")
    else:
        # Apply preset override if provided via CLI
        effective_config = dict(config)
        if preset:
            effective_config["horizon_preset"] = preset
            print(f"Using preset override: {preset}")
        periods_seconds = tiers_to_periods_seconds(effective_config, start_time=start_dt)
        print(f"Optimization periods: {len(periods_seconds)} intervals (from config)")

        if not periods_seconds:
            print("Error: No periods configured")
            sys.exit(1)

        effective_start = start_dt.timestamp() if start_dt else start_time
        forecast_times = generate_forecast_timestamps(periods_seconds, effective_start)
        print(f"Forecast horizon: {len(forecast_times)} boundaries (generated)")

    if not periods_seconds or not forecast_times:
        print("Error: Failed to build forecast timeline")
        sys.exit(1)

    # Normalize participant config shape before loading values:
    # - migration handles legacy/mixed config layout
    # - load_element_data handles schema value unwrapping and sensor resolution
    for element_name, element_config in list(participants_config.items()):
        participants_config[element_name] = normalize_participant_config_for_diag(element_name, element_config)

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
    periods_hours = np.asarray(periods_seconds, dtype=float) / 3600
    network = Network(name="diag", periods=periods_hours)
    for elem in collect_model_elements(loaded_participants):
        network.add(elem)
    print(f"Network elements: {list(network.elements.keys())}")

    print("\nRunning optimization...")
    try:
        cost = network.optimize()
        print(f"Optimization complete. Total cost: ${cost:.2f}")
    except Exception as e:
        print(f"Optimization failed: {e}")
        sys.exit(1)

    # Format and print results
    if compare:
        # Extract data from both sources
        if not diag.outputs:
            print("Error: No outputs in diagnostics file for comparison")
            sys.exit(1)

        diag_rows = extract_rows_from_diagnostics(diag.outputs, timezone_str, config)
        rerun_rows = extract_rows_from_network(network, loaded_participants, forecast_times, timezone_str)
        table = format_comparison_table(diag_rows, rerun_rows, timezone_str)
    else:
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
    uv run diag --file diagnostics.json --compare
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
    parser.add_argument(
        "--compare",
        "-c",
        action="store_true",
        help="Compare diagnostics outputs vs rerun optimization side-by-side",
    )
    parser.add_argument(
        "--preset",
        "-p",
        choices=["2_days", "3_days", "5_days", "7_days"],
        help="Override horizon preset for tier alignment (use when diagnostics lacks preset)",
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    if args.compare and args.outputs_only:
        print("Warning: --compare implies running optimization, ignoring --outputs-only")

    run_diagnostics(args.file, outputs_only=args.outputs_only, compare=args.compare, preset=args.preset)


if __name__ == "__main__":
    main()

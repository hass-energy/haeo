#!/usr/bin/env -S uv run python
"""Transform sensor data with various timestamp adjustments.

This script provides transformations for Home Assistant command_line sensors:
- day_offset: Shift timestamps by N days (solar forecasts)
- wrap_forecasts: Reorder forecasts starting from current time-of-day (Amber Electric)
- passthrough: Return data unchanged (static sensors)
"""

import argparse
from datetime import UTC, datetime, timedelta
import json
import logging
from pathlib import Path
import sys
from typing import Any

# Type aliases for clarity
type JSONDict = dict[str, Any]
type ForecastList = list[JSONDict]

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)


def _transform_timestamp(ts_str: str, target_day_ts: float) -> str:
    """Transform a single ISO 8601 timestamp string to target day while preserving time-of-day.

    Args:
        ts_str: ISO 8601 timestamp string (may include timezone)
        target_day_ts: Unix timestamp for target day at midnight UTC

    Returns:
        Transformed ISO 8601 timestamp string in original format

    """
    try:
        ts = datetime.fromisoformat(ts_str)
        original_tz = ts.tzinfo

        # Extract time components from original timezone representation
        time_components = (ts.hour, ts.minute, ts.second)

        # Create target day at midnight UTC
        target_day_utc = datetime.fromtimestamp(target_day_ts, tz=UTC)

        # Handle timezone-aware timestamps
        if original_tz is not None and original_tz != UTC:
            target_day_local = target_day_utc.astimezone(original_tz)
            new_ts = target_day_local.replace(
                hour=time_components[0],
                minute=time_components[1],
                second=time_components[2],
            )
            return new_ts.isoformat()

        # UTC timezone - create timestamp at target day + time offset
        time_offset_seconds = time_components[0] * 3600 + time_components[1] * 60 + time_components[2]
        new_ts_utc = datetime.fromtimestamp(target_day_ts + time_offset_seconds, tz=UTC)
        return new_ts_utc.isoformat().replace("+00:00", "Z")

    except (ValueError, AttributeError):
        logger.debug("Could not parse timestamp: %s", ts_str)
        return ts_str


def _transform_value_recursive(value: Any, transform_fn: Any) -> Any:
    """Recursively transform timestamps in any data structure.

    Args:
        value: Value to transform (string, dict, list, or other)
        transform_fn: Function to apply to string values

    Returns:
        Transformed value with same structure as input

    """
    if isinstance(value, str):
        return transform_fn(value)
    if isinstance(value, dict):
        return {transform_fn(k): _transform_value_recursive(v, transform_fn) for k, v in value.items()}
    if isinstance(value, list):
        return [_transform_value_recursive(item, transform_fn) for item in value]
    return value


def shift_day_offset(data: JSONDict, day_offset: int) -> JSONDict:
    """Shift timestamps in data by day_offset days (for solar sensors).

    Finds all ISO 8601 timestamps in the data and shifts them to the target day
    while preserving the time-of-day component in the original timezone.

    Args:
        data: Sensor data dictionary with potential timestamp fields
        day_offset: Number of days to shift (0=today, 1=tomorrow, etc.)

    Returns:
        Data with all timestamps shifted by day_offset days

    """
    now = datetime.now(UTC)
    today_midnight_utc = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_per_day = 86400
    target_day_ts = today_midnight_utc.timestamp() + (day_offset * seconds_per_day)

    def transform_fn(ts_str: str) -> str:
        return _transform_timestamp(ts_str, target_day_ts)

    return _transform_value_recursive(data, transform_fn)  # type: ignore[no-any-return]


def _parse_forecast_times(forecasts: ForecastList) -> list[tuple[datetime, JSONDict]]:
    """Parse forecast list into (timestamp, forecast) tuples.

    Args:
        forecasts: List of forecast dictionaries with time fields

    Returns:
        List of (timestamp, forecast) tuples sorted by time.
        Uses nem_date (local time) for timezone-aware matching, falls back to start_time.

    """
    forecast_times = []
    for forecast in forecasts:
        # Prefer nem_date (local time) for matching; fall back to start_time
        time_str = forecast.get("nem_date") or forecast.get("start_time")
        if not time_str:
            continue

        try:
            timestamp = datetime.fromisoformat(time_str)
            forecast_times.append((timestamp, forecast))
        except (ValueError, AttributeError):
            logger.debug("Could not parse forecast time: %s", time_str)

    forecast_times.sort(key=lambda x: x[0])
    return forecast_times


def _find_closest_time_of_day_index(
    forecast_times: list[tuple[datetime, JSONDict]],
    window_start: datetime,
) -> int:
    """Find index of forecast closest to current time-of-day.

    Uses modular arithmetic on actual time differences, which is timezone-agnostic.

    Args:
        forecast_times: Sorted list of (timestamp, forecast) tuples
        window_start: Window start datetime to match against

    Returns:
        Index of forecast with closest matching time-of-day

    """
    if not forecast_times:
        return 0

    seconds_per_day = 86400
    closest_idx = 0
    min_offset = float("inf")

    for i, (timestamp, _) in enumerate(forecast_times):
        # Time difference mod 24 hours gives within-day offset
        diff_seconds = (window_start - timestamp).total_seconds() % seconds_per_day
        # Consider both directions (e.g., 23 hours ahead vs 1 hour behind)
        offset = min(diff_seconds, seconds_per_day - diff_seconds)

        if offset < min_offset:
            min_offset = offset
            closest_idx = i

    return closest_idx


def _transform_forecast_timestamps(
    forecast: JSONDict,
    time_delta: timedelta,
) -> JSONDict:
    """Apply time delta to all timestamp fields in forecast.

    Args:
        forecast: Forecast dictionary with timestamp fields
        time_delta: Time delta to add to all timestamps

    Returns:
        Forecast with transformed timestamps

    """
    transformed = forecast.copy()

    for key in ["start_time", "end_time", "nem_date"]:
        if key not in transformed:
            continue

        try:
            old_ts = datetime.fromisoformat(transformed[key])
            new_ts = old_ts + time_delta

            # Preserve original format (Z suffix or ISO format)
            if transformed[key].endswith("Z"):
                transformed[key] = new_ts.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
            else:
                transformed[key] = new_ts.isoformat()
        except (ValueError, AttributeError):
            logger.debug("Could not transform timestamp field %s: %s", key, transformed[key])

    # Handle date field
    if "date" in transformed:
        try:
            date_str = transformed["date"]
            if "T" in date_str:
                date_str = date_str.split("T")[0]
            old_date = datetime.fromisoformat(date_str)
            new_date = old_date + time_delta
            transformed["date"] = new_date.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            logger.debug("Could not transform date field: %s", transformed["date"])

    return transformed


def wrap_forecasts(data: JSONDict) -> JSONDict:
    """Create 24-hour forecast window starting from current time-of-day (for Amber sensors).

    Takes forecasts from the current time onwards and wraps around to show exactly
    24 hours. Adjusts timestamps to show the 24-hour window starting from now.

    Args:
        data: Sensor data with "attributes.forecasts" list

    Returns:
        Data with forecasts reordered and timestamps adjusted to start from now

    """
    if "attributes" not in data or "forecasts" not in data["attributes"]:
        logger.debug("No forecasts found in data")
        return data

    forecasts = data["attributes"]["forecasts"]
    if not forecasts:
        logger.debug("Empty forecasts list")
        return data

    now = datetime.now(UTC)
    # Round down to nearest hour to align with forecast boundaries
    window_start = now.replace(second=0, microsecond=0, minute=0)
    forecast_times = _parse_forecast_times(forecasts)

    if not forecast_times:
        logger.warning("No valid forecast times found")
        return data

    closest_idx = _find_closest_time_of_day_index(forecast_times, window_start)
    first_forecast_time = forecast_times[closest_idx][0]

    # Calculate delta directly - datetime subtraction handles timezone conversion
    base_time_delta = window_start - first_forecast_time

    # Calculate wrap duration (time span of entire forecast period + gap)
    last_time = forecast_times[-1][0]
    first_time = forecast_times[0][0]
    forecast_duration_seconds = (last_time - first_time).total_seconds()
    gap_seconds = 300  # 5 minute gap between periods
    wrap_duration = timedelta(seconds=forecast_duration_seconds + gap_seconds)

    window_forecasts = []
    for i in range(len(forecast_times)):
        idx = (closest_idx + i) % len(forecast_times)
        _, forecast = forecast_times[idx]

        # All forecasts shift by base_time_delta (the date shift + time alignment)
        # Wrapped forecasts also add wrap_duration to push them to the next cycle
        adjusted_delta = base_time_delta + wrap_duration if idx < closest_idx else base_time_delta

        transformed_forecast = _transform_forecast_timestamps(forecast, adjusted_delta)
        window_forecasts.append(transformed_forecast)

    data["attributes"]["forecasts"] = window_forecasts
    return data


def passthrough(data: JSONDict) -> JSONDict:
    """Pass data through unchanged (for SiGen and Amber price sensors).

    Args:
        data: Sensor data dictionary

    Returns:
        Unchanged sensor data

    """
    return data


def _read_json_file(json_file: Path) -> JSONDict:
    """Read and parse JSON file.

    Args:
        json_file: Path to JSON file

    Returns:
        Parsed JSON data as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON

    """
    try:
        with json_file.open() as f:
            result: JSONDict = json.load(f)
            return result
    except FileNotFoundError:
        logger.exception("JSON file not found: %s", json_file)
        raise
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in %s", json_file)
        raise


def _apply_transform(
    data: JSONDict,
    transform_type: str,
    day_offset: int | None = None,
) -> JSONDict:
    """Apply specified transformation to data.

    Args:
        data: Sensor data to transform
        transform_type: Type of transformation (day_offset, wrap_forecasts, passthrough)
        day_offset: Days to shift (required for day_offset transform)

    Returns:
        Transformed sensor data

    Raises:
        ValueError: If transform_type is unknown or day_offset missing when required

    """
    if transform_type == "day_offset":
        if day_offset is None:
            msg = "day_offset transform requires --day-offset parameter"
            raise ValueError(msg)
        return shift_day_offset(data, day_offset)

    if transform_type == "wrap_forecasts":
        return wrap_forecasts(data)

    if transform_type == "passthrough":
        return passthrough(data)

    msg = f"Unknown transform type: {transform_type}"
    raise ValueError(msg)


def _create_argument_parser() -> argparse.ArgumentParser:
    """Create argument parser for transform_sensor CLI.

    Returns:
        Configured ArgumentParser instance

    """
    parser = argparse.ArgumentParser(
        description="Transform Home Assistant sensor JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Transform types:
  day_offset      Shift timestamps by N days (requires --day-offset)
  wrap_forecasts  Reorder forecasts to start from current time-of-day
  passthrough     Return data unchanged

Examples:
  %(prog)s sensor.json day_offset --day-offset 0      # Today (no shift)
  %(prog)s sensor.json day_offset --day-offset 1      # Tomorrow
  %(prog)s sensor.json wrap_forecasts                 # Amber forecasts
  %(prog)s sensor.json passthrough                    # Static sensors
        """,
    )

    parser.add_argument(
        "json_file",
        type=Path,
        help="Path to JSON sensor data file",
    )

    parser.add_argument(
        "transform_type",
        choices=["day_offset", "wrap_forecasts", "passthrough"],
        help="Type of transformation to apply",
    )

    parser.add_argument(
        "--day-offset",
        type=int,
        metavar="N",
        help="Number of days to shift timestamps (required for day_offset)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    return parser


def main() -> int:
    """Run sensor transformation CLI.

    Returns:
        Exit code (0 for success, 1 for error)

    """
    parser = _create_argument_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")

    try:
        data = _read_json_file(args.json_file)
        logger.debug("Read JSON from %s", args.json_file)

        transformed = _apply_transform(data, args.transform_type, args.day_offset)
        logger.debug("Applied %s transform", args.transform_type)

        # Output to stdout (JSON only, no logging)
        print(json.dumps(transformed))  # noqa: T201
        return 0

    except (FileNotFoundError, json.JSONDecodeError):
        logger.exception("Failed to read JSON file")
        return 1
    except ValueError:
        logger.exception("Invalid transform parameters")
        return 1
    except Exception:  # Broad exception handling for CLI entry point
        logger.exception("Unexpected error occurred")
        return 1


if __name__ == "__main__":
    sys.exit(main())

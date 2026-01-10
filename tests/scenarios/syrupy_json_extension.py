"""Custom syrupy extension to serialize sensor snapshots into outputs.json files."""

from collections.abc import Mapping, Sequence
import json
from numbers import Real
from pathlib import Path
from typing import Any

from syrupy.extensions.json import JSONSnapshotExtension
from syrupy.location import PyTestLocation
from syrupy.types import SerializableData, SerializedData, SnapshotIndex


def _try_parse_float(value: Any) -> float | None:
    """Try to parse a value as a float."""
    if isinstance(value, Real):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def approx_equal(a: Any, b: Any, rel_tol: float = 0.1, abs_tol: float = 1e-6, path: str = "") -> bool:
    """Compare two values with approximate equality for floats.

    For floats, uses relative and absolute tolerance.
    For numeric strings, converts to float and uses approximate comparison.
    For other types, uses exact equality.
    Recursively handles nested dicts and lists.

    The default tolerance of 10% (rel_tol=0.1) is chosen to accommodate
    naturally variable values like optimizer timing.
    """
    # Handle None cases
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False

    # Handle floats with approximate comparison
    if isinstance(a, Real) and isinstance(b, Real):
        if a == b:  # Handle exact matches, infinity, etc.
            return True
        return abs(float(a) - float(b)) <= max(rel_tol * max(abs(float(a)), abs(float(b))), abs_tol)

    # Handle numeric strings with approximate comparison
    if isinstance(a, str) and isinstance(b, str):
        a_float = _try_parse_float(a)
        b_float = _try_parse_float(b)
        if a_float is not None and b_float is not None:
            if a_float == b_float:  # Handle exact matches
                return True
            return abs(a_float - b_float) <= max(rel_tol * max(abs(a_float), abs(b_float)), abs_tol)
        # Not both numeric strings, fall through to exact equality

    # Handle dicts recursively
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        if set(a) != set(b):
            return False
        return all(approx_equal(a[key], b[key], rel_tol, abs_tol, path=f"{path}.{key}") for key in a)

    # Handle lists/sequences recursively
    if isinstance(a, Sequence) and isinstance(b, Sequence) and not isinstance(a, str) and not isinstance(b, str):
        if len(a) != len(b):
            return False
        return all(
            approx_equal(a_item, b_item, rel_tol, abs_tol, path=f"{path}[{i}]")
            for i, (a_item, b_item) in enumerate(zip(a, b, strict=True))
        )

    # For all other types, use exact equality
    result: bool = a == b
    return result


class ScenarioJSONExtension(JSONSnapshotExtension):
    """Custom syrupy extension for storing snapshots in outputs.json.

    This extension:
    - Stores sensor data as Python dicts (not JSON strings)
    - Writes directly to outputs.json in scenario directory
    - Uses approximate float comparison for robustness
    - Expects sensor data from get_output_sensors() with datetime keys already converted to ISO strings
    """

    def serialize(
        self,
        data: SerializableData,
        *,
        exclude: Any = None,
        include: Any = None,
        matcher: Any = None,
    ) -> SerializedData:
        """Serialize sensor data to Python dict for JSON storage.

        Unlike the parent class which returns a JSON string, we return a Python dict
        directly so it can be written to outputs.json with consistent formatting.

        The parent's _filter() method is now safe to use because datetime keys have
        already been converted to ISO strings by get_output_sensors(), so they won't
        be stripped out by the string key requirement.

        Args:
            data: Sensor data to serialize (already has ISO string keys for forecasts)
            exclude: Property filter to exclude certain fields (passed to parent)
            include: Property filter to include only certain fields (passed to parent)
            matcher: Property matcher for custom transformations (passed to parent)

        Returns:
            Python dict (not JSON string) for direct storage in outputs.json.

        """
        # Apply parent class filtering for property exclusion/inclusion/matching
        # Return dict directly (parent's serialize() would convert to JSON string)
        # Note: We intentionally return a dict instead of str|bytes for direct JSON storage
        filtered: SerializedData = self._filter(
            data=data,
            depth=0,
            path=(),
            exclude=exclude,
            include=include,
            matcher=matcher,
        )
        return filtered

    @classmethod
    def _get_scenario_dir(cls, test_location: PyTestLocation) -> Path:
        """Extract scenario directory from test location.

        Test name format: test_scenario[scenario_path]
        Extracts scenario_path (e.g., "scenario1").
        """
        testname = test_location.testname

        # Extract scenario name from parameterized test name
        # Format: test_scenario[/path/to/scenario1]
        if "[" in testname and "]" in testname:
            param_part = testname[testname.index("[") + 1 : testname.index("]")]
            scenario_name = Path(param_part).name
        else:
            scenario_name = testname

        # Return path to scenario directory
        test_scenarios_dir = Path(__file__).parent
        return test_scenarios_dir / scenario_name

    @classmethod
    def write_snapshot(
        cls,
        *,
        snapshot_location: str,  # noqa: ARG003
        snapshots: list[tuple[SerializedData, PyTestLocation, SnapshotIndex]],
    ) -> None:
        """Write snapshot data directly to outputs.json.

        Args:
            snapshot_location: Unused (required by interface)
            snapshots: List of (serialized_data, test_location, index) tuples

        """
        # Extract test location and data from first snapshot
        output_data, test_location, _ = snapshots[0]

        # Get scenario directory and outputs file path
        scenario_dir = cls._get_scenario_dir(test_location)
        outputs_file = scenario_dir / "outputs.json"

        # Write outputs directly to outputs.json
        with outputs_file.open("w") as f:
            json.dump(output_data, f, indent=2)
            f.write("\n")  # POSIX trailing newline

    def read_snapshot(
        self,
        *,
        index: SnapshotIndex = 0,  # noqa: ARG002
        session_id: str,  # noqa: ARG002
        test_location: PyTestLocation,
    ) -> SerializableData:
        """Read snapshot data directly from outputs.json.

        Returns: Python dict matching format from get_output_sensors().
        """
        scenario_dir = self.__class__._get_scenario_dir(test_location)
        outputs_file = scenario_dir / "outputs.json"

        if not outputs_file.exists():
            return {}

        with outputs_file.open() as f:
            return json.load(f)

    def matches(
        self,
        *,
        serialized_data: SerializableData,
        snapshot_data: SerializableData,
    ) -> bool:
        """Compare serialized data with snapshot using approximate float comparison."""
        return approx_equal(serialized_data, snapshot_data)

"""Element-layer optimization tests.

These tests verify that the element layer correctly:
1. Creates model elements from config data
2. Runs optimization through the Network
3. Aggregates model outputs into device outputs

Uses the VALID test cases which contain model element definitions and expected outputs.
"""

from typing import Any

import pytest

from custom_components.haeo.elements import ELEMENT_TYPES, ElementConfigData, ElementConfigSchema, ElementType
from custom_components.haeo.model.network import Network
from tests.test_data.elements import VALID_CONFIGS_BY_TYPE, ElementValidCase

# Model element constructors by element_type string
MODEL_ELEMENT_TYPES: dict[str, str] = {
    "battery": "battery",
    "source_sink": "source_sink",
    "connection": "connection",
}


def _all_valid_cases() -> list[tuple[ElementType, ElementValidCase[ElementConfigSchema, ElementConfigData]]]:
    return [(element_type, case) for element_type, cases in VALID_CONFIGS_BY_TYPE.items() for case in cases]


def _case_ids() -> list[str]:
    return [
        case.get("description", f"{element_type}_{i}")
        for element_type, cases in VALID_CONFIGS_BY_TYPE.items()
        for i, case in enumerate(cases)
    ]


@pytest.mark.parametrize(("element_type", "case"), _all_valid_cases(), ids=_case_ids())
def test_element_optimization(
    element_type: ElementType, case: ElementValidCase[ElementConfigSchema, ElementConfigData]
) -> None:
    """Verify element layer produces valid outputs after optimization.

    This test uses the VALID test cases to verify the full optimization pipeline:
    1. Creates model elements from the case's "model" definitions
    2. Runs optimization on the network
    3. Verifies the adapter correctly transforms model outputs to device outputs
    """
    entry = ELEMENT_TYPES[element_type]
    data = case["data"]
    model_elements = case["model"]

    # Determine periods from data arrays (use capacity as representative)
    periods = _get_periods_from_data(data)
    if not periods:
        pytest.skip("Cannot determine periods from data")

    # Create network with the given periods
    network = Network(name="test_network", periods=periods)

    # Find and add external connection target (e.g., "network") as a source_sink
    external_targets = _find_external_targets(model_elements)
    for target_name in external_targets:
        network.add("source_sink", target_name, is_source=True, is_sink=True)

    # Add all model elements to the network
    for model_element in model_elements:
        config = dict(model_element)  # Copy to avoid mutating original
        element_type_str = config.pop("element_type")
        name = config.pop("name")
        network.add(element_type_str, name, **config)

    # Run optimization
    network.optimize()

    # Collect model outputs from all network elements
    model_outputs = {name: element.outputs() for name, element in network.elements.items()}

    # Get aggregated device outputs using the element adapter
    result = entry.outputs(data["name"], model_outputs, data)

    # Verify the adapter produces all expected device outputs
    expected_outputs = case["outputs"]
    for device_name in expected_outputs:
        assert device_name in result, f"Missing device {device_name} in result"

        # Verify all expected output keys exist (values may differ from mocked expectations)
        for output_name in expected_outputs[device_name]:
            assert output_name in result[device_name], f"Missing output {output_name} in device {device_name}"

            # Verify output has correct type and unit
            expected = expected_outputs[device_name][output_name]
            actual = result[device_name][output_name]
            assert actual.type == expected.type, (
                f"Type mismatch for {device_name}.{output_name}: expected {expected.type}, got {actual.type}"
            )
            assert actual.unit == expected.unit, (
                f"Unit mismatch for {device_name}.{output_name}: expected {expected.unit}, got {actual.unit}"
            )


def _get_periods_from_data(data: ElementConfigData) -> list[float]:
    """Extract period durations from data arrays.

    Returns 1-hour periods based on the length of array fields in data.
    """
    # Look for array fields that indicate number of periods
    for key in ("capacity", "max_charge_power", "max_discharge_power", "power", "forecast"):
        if key in data:
            value = data[key]  # type: ignore[literal-required]
            if isinstance(value, (list, tuple)) and len(value) > 0:
                return [1.0] * len(value)
    return []


def _find_external_targets(model_elements: list[dict[str, Any]]) -> set[str]:
    """Find connection targets that aren't defined in the model elements.

    These represent external elements (like "network") that need to be created.
    """
    defined_names = {elem.get("name") for elem in model_elements if "name" in elem}
    external_targets: set[str] = set()

    for elem in model_elements:
        if elem.get("element_type") == "connection":
            target = elem.get("target")
            if target and target not in defined_names:
                external_targets.add(target)

    return external_targets

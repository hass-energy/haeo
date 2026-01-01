"""Test that all output names and device names have translation keys."""

import json
from pathlib import Path

import pytest

from custom_components.haeo.elements import ELEMENT_DEVICE_NAMES, ELEMENT_OUTPUT_NAMES
from custom_components.haeo.flows.field_schema import InputMode


def test_all_output_names_have_translations() -> None:
    """Verify that every output name from all elements has a translation in en.json."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    sensor_translations = translations.get("entity", {}).get("sensor", {})

    # Check each output name using list comprehension
    missing_translations = [n for n in ELEMENT_OUTPUT_NAMES if n not in sensor_translations]

    if missing_translations:
        pytest.fail(
            f"The following output names are missing translations in en.json:\n"
            f"{', '.join(missing_translations)}\n\n"
            f"Add them to custom_components/haeo/translations/en.json under entity.sensor"
        )


def test_no_unused_translations() -> None:
    """Verify that there are no unused translation keys (helps catch renamed outputs)."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    sensor_translations = translations.get("entity", {}).get("sensor", {})

    # Known non-element sensor translation keys (e.g., horizon entity)
    known_non_element_keys = {"horizon"}

    # Check for unused translations using list comprehension
    unused_translations = [
        k
        for k in sorted(sensor_translations.keys())
        if k not in ELEMENT_OUTPUT_NAMES and k not in known_non_element_keys
    ]

    if unused_translations:
        pytest.fail(
            f"The following translation keys in en.json are not used by any element:\n"
            f"{', '.join(unused_translations)}\n\n"
            f"Either remove them or add the corresponding output to an element's outputs() method"
        )


def test_all_device_names_have_translations() -> None:
    """Verify that every device name from all elements has a translation in en.json."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    device_translations = translations.get("device", {})

    # Check each device name using list comprehension
    missing_translations = [n for n in ELEMENT_DEVICE_NAMES if n not in device_translations]

    if missing_translations:
        pytest.fail(
            f"The following device names are missing translations in en.json:\n"
            f"{', '.join(missing_translations)}\n\n"
            f"Add them to custom_components/haeo/translations/en.json under device"
        )


def test_no_unused_device_translations() -> None:
    """Verify that there are no unused device translation keys."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    device_translations = translations.get("device", {})

    # Network is a special case - it's the hub device, not an element adapter
    special_device_types = {"network"}

    # Check for unused device translations
    all_known_devices = ELEMENT_DEVICE_NAMES | special_device_types
    unused_translations = [k for k in sorted(device_translations.keys()) if k not in all_known_devices]

    if unused_translations:
        pytest.fail(
            f"The following device translation keys in en.json are not used:\n"
            f"{', '.join(unused_translations)}\n\n"
            f"Either remove them or add the corresponding device to an element's DEVICE_NAMES"
        )


def test_input_mode_selector_translations() -> None:
    """Verify that all input mode options have translations in the selector section."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    selector_translations = translations.get("selector", {})

    # Check that input_mode selector exists
    if "input_mode" not in selector_translations:
        pytest.fail(
            "Missing 'input_mode' in selector translations.\n\n"
            "Add it to custom_components/haeo/translations/en.json under selector.input_mode"
        )

    input_mode_options = selector_translations["input_mode"].get("options", {})

    # Check that all InputMode enum values have translations
    missing_translations = [mode.value for mode in InputMode if mode.value not in input_mode_options]

    if missing_translations:
        pytest.fail(
            f"The following input mode options are missing translations:\n"
            f"{', '.join(missing_translations)}\n\n"
            f"Add them to custom_components/haeo/translations/en.json under selector.input_mode.options"
        )

    # Check no extra options exist
    extra_options = [opt for opt in input_mode_options if opt not in [mode.value for mode in InputMode]]

    if extra_options:
        pytest.fail(
            f"The following selector options are not valid InputMode values:\n"
            f"{', '.join(extra_options)}\n\n"
            f"Remove them from selector.input_mode.options or add them to the InputMode enum"
        )

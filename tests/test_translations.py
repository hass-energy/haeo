"""Test that all output names and device names have translation keys."""

import json
from pathlib import Path

import pytest

from custom_components.haeo.elements import ELEMENT_DEVICE_NAMES, ELEMENT_OUTPUT_NAMES


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

    # Check for unused translations using list comprehension
    unused_translations = [k for k in sorted(sensor_translations.keys()) if k not in ELEMENT_OUTPUT_NAMES]

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

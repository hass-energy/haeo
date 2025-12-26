"""Test that all output names and device names have translation keys."""

import json
from pathlib import Path

import pytest

from custom_components.haeo.elements import ELEMENT_DEVICE_NAMES, ELEMENT_OUTPUT_NAMES
from custom_components.haeo.schema.input_fields import InputEntityType, get_all_input_fields


def test_all_output_names_have_sensor_translations() -> None:
    """Verify that every OUTPUT_NAME has a translation in en.json under entity.sensor."""
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    sensor_translations = translations.get("entity", {}).get("sensor", {})

    # Only OUTPUT_NAMES should be in entity.sensor
    missing_translations = [n for n in ELEMENT_OUTPUT_NAMES if n not in sensor_translations]

    if missing_translations:
        pytest.fail(
            f"The following output names are missing translations in en.json:\n"
            f"{', '.join(sorted(missing_translations))}\n\n"
            f"Add them to custom_components/haeo/translations/en.json under entity.sensor"
        )


def test_all_input_fields_have_number_or_switch_translations() -> None:
    """Verify that every input field has a translation in en.json under entity.number or entity.switch."""
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    number_translations = translations.get("entity", {}).get("number", {})
    switch_translations = translations.get("entity", {}).get("switch", {})

    missing_translations = []
    all_input_fields = get_all_input_fields()

    for input_fields in all_input_fields.values():
        for field_info in input_fields:
            translation_key = field_info.translation_key
            if not translation_key:
                continue

            if field_info.entity_type == InputEntityType.SWITCH:
                if translation_key not in switch_translations:
                    missing_translations.append(f"{translation_key} (switch)")
            elif translation_key not in number_translations:
                missing_translations.append(f"{translation_key} (number)")

    if missing_translations:
        pytest.fail(
            f"The following input fields are missing translations in en.json:\n"
            f"{', '.join(sorted(missing_translations))}\n\n"
            f"Add them to custom_components/haeo/translations/en.json under entity.number or entity.switch"
        )


def test_no_unused_sensor_translations() -> None:
    """Verify that there are no unused translation keys in entity.sensor."""
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    sensor_translations = translations.get("entity", {}).get("sensor", {})

    # Only OUTPUT_NAMES should be in entity.sensor
    unused_translations = [k for k in sorted(sensor_translations.keys()) if k not in ELEMENT_OUTPUT_NAMES]

    if unused_translations:
        pytest.fail(
            f"The following sensor translation keys in en.json are not used by any element:\n"
            f"{', '.join(unused_translations)}\n\n"
            f"Either remove them or add the corresponding output to an element's OUTPUT_NAMES"
        )


def test_no_unused_number_or_switch_translations() -> None:
    """Verify that there are no unused translation keys in entity.number or entity.switch."""
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    number_translations = translations.get("entity", {}).get("number", {})
    switch_translations = translations.get("entity", {}).get("switch", {})

    # Collect all translation_keys from input fields
    expected_number_keys: set[str] = set()
    expected_switch_keys: set[str] = set()

    all_input_fields = get_all_input_fields()
    for input_fields in all_input_fields.values():
        for field_info in input_fields:
            translation_key = field_info.translation_key
            if not translation_key:
                continue

            if field_info.entity_type == InputEntityType.SWITCH:
                expected_switch_keys.add(translation_key)
            else:
                expected_number_keys.add(translation_key)

    unused_number = [k for k in sorted(number_translations.keys()) if k not in expected_number_keys]
    unused_switch = [k for k in sorted(switch_translations.keys()) if k not in expected_switch_keys]

    unused_all = []
    if unused_number:
        unused_all.extend(f"{k} (number)" for k in unused_number)
    if unused_switch:
        unused_all.extend(f"{k} (switch)" for k in unused_switch)

    if unused_all:
        pytest.fail(
            f"The following number/switch translation keys in en.json are not used:\n"
            f"{', '.join(unused_all)}\n\n"
            f"Either remove them or add the corresponding input field to an element's ConfigSchema"
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

"""Test that all output names have translation keys."""

import json
from pathlib import Path

import pytest

from custom_components.haeo.model.output_names import ALL_OUTPUT_NAMES


def test_all_output_names_have_translations() -> None:
    """Verify that every output name from all elements has a translation in en.json."""
    # Load translations directly from file
    translations_path = Path(__file__).parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with translations_path.open() as f:
        translations = json.load(f)

    sensor_translations = translations.get("entity", {}).get("sensor", {})

    # Check each output name using list comprehension
    missing_translations = [
        output_name for output_name in sorted(ALL_OUTPUT_NAMES) if output_name not in sensor_translations
    ]

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
    unused_translations = [
        translation_key
        for translation_key in sorted(sensor_translations.keys())
        if translation_key not in ALL_OUTPUT_NAMES
    ]

    if unused_translations:
        pytest.fail(
            f"The following translation keys in en.json are not used by any element:\n"
            f"{', '.join(unused_translations)}\n\n"
            f"Either remove them or add the corresponding output to an element's outputs() method"
        )

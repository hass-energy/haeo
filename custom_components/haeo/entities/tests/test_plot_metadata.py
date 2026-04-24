"""Tests for the plot_metadata helpers."""

import pytest

from custom_components.haeo.entities.plot_metadata import (
    SOURCE_ROLE_FORECAST,
    SOURCE_ROLE_LIMIT,
    SOURCE_ROLE_OUTPUT,
    classify_source_role,
)


@pytest.mark.parametrize(
    ("config_mode", "field_name", "expected"),
    [
        (None, None, SOURCE_ROLE_OUTPUT),
        (None, "forecast", SOURCE_ROLE_OUTPUT),
        ("editable", "forecast", SOURCE_ROLE_FORECAST),
        ("driven", "forecast", SOURCE_ROLE_FORECAST),
        ("editable", "max_power", SOURCE_ROLE_LIMIT),
        ("driven", None, SOURCE_ROLE_LIMIT),
    ],
)
def test_classify_source_role(config_mode: str | None, field_name: str | None, expected: str) -> None:
    """Source role is classified based on config mode and field name."""
    assert classify_source_role(config_mode, field_name) == expected

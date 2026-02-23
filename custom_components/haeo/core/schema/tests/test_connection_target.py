"""Tests for connection target schema helpers."""

from typing import Any, cast

import pytest

from custom_components.haeo.core.schema.connection_target import (
    VALUE_TYPE_CONNECTION_TARGET,
    as_connection_target,
    get_connection_target_name,
    is_connection_target,
    normalize_connection_target,
)


def test_is_connection_target_checks_mapping() -> None:
    """is_connection_target validates mapping structure and types."""
    assert is_connection_target("bus") is False
    assert is_connection_target({"type": "other", "value": "bus"}) is False
    assert is_connection_target({"type": VALUE_TYPE_CONNECTION_TARGET, "value": 123}) is False
    assert is_connection_target({"type": VALUE_TYPE_CONNECTION_TARGET, "value": "bus"}) is True


def test_normalize_connection_target_handles_str_and_schema_value() -> None:
    """normalize_connection_target accepts str and schema values."""
    schema_value = as_connection_target("bus")
    assert normalize_connection_target("bus") == schema_value
    assert normalize_connection_target(schema_value) == schema_value


def test_normalize_connection_target_rejects_invalid_type() -> None:
    """normalize_connection_target rejects unsupported input types."""
    with pytest.raises(TypeError, match="Unsupported connection target"):
        normalize_connection_target(cast("Any", 123))


def test_get_connection_target_name_handles_variants() -> None:
    """get_connection_target_name returns names for all supported inputs."""
    assert get_connection_target_name(None) is None
    assert get_connection_target_name("bus") == "bus"
    assert get_connection_target_name(as_connection_target("bus")) == "bus"


def test_get_connection_target_name_rejects_invalid_type() -> None:
    """get_connection_target_name rejects unsupported input types."""
    with pytest.raises(TypeError, match="Unsupported connection target"):
        get_connection_target_name(cast("Any", 123))

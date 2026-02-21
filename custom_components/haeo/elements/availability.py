"""Shared availability checks for element adapters."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from custom_components.haeo.core.state import StateMachine
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.schema import (
    VALUE_TYPE_CONSTANT,
    VALUE_TYPE_ENTITY,
    VALUE_TYPE_NONE,
    is_connection_target,
    is_schema_value,
)


def schema_config_available(config: Mapping[str, Any], *, sm: StateMachine) -> bool:
    """Return True when every entity-backed schema value is available."""
    ts_loader = TimeSeriesLoader()
    return _mapping_available(config, sm=sm, ts_loader=ts_loader)


def _mapping_available(
    mapping: Mapping[str, Any],
    *,
    sm: StateMachine,
    ts_loader: TimeSeriesLoader,
) -> bool:
    for value in mapping.values():
        if value is None:
            continue

        if is_schema_value(value):
            if value["type"] == VALUE_TYPE_ENTITY:
                if not ts_loader.available(sm=sm, value=value):
                    return False
            elif value["type"] in (VALUE_TYPE_CONSTANT, VALUE_TYPE_NONE):
                continue
            continue

        if is_connection_target(value):
            continue

        if isinstance(value, Mapping) and not _mapping_available(value, sm=sm, ts_loader=ts_loader):
            return False

    return True

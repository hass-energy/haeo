"""Pure config transformation logic for v1.4 connection unidirectional migration."""

from __future__ import annotations

from typing import Any

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import get_connection_target_name, normalize_connection_target
from custom_components.haeo.core.schema.elements import connection
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

_REVERSE_TO_FORWARD: tuple[tuple[str, str], ...] = (
    (CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET),
    (CONF_PRICE_TARGET_SOURCE, CONF_PRICE_SOURCE_TARGET),
    (CONF_EFFICIENCY_TARGET_SOURCE, CONF_EFFICIENCY_SOURCE_TARGET),
)

_REVERSE_SECTIONS: tuple[str, ...] = (SECTION_POWER_LIMITS, SECTION_PRICING, SECTION_EFFICIENCY)


def _is_configured_value(value: Any) -> bool:
    """Return True when a schema value represents an active configuration."""
    return value is not None and not (isinstance(value, dict) and value.get("type") == "none")


def _section_dict(data: dict[str, Any], section: str) -> dict[str, Any]:
    section_data = data.get(section, {})
    return dict(section_data) if isinstance(section_data, dict) else {}


def _strip_reverse_from_section(section_data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Remove reverse-direction keys and return extracted reverse values."""
    reverse_values: dict[str, Any] = {}
    cleaned = dict(section_data)
    for reverse_key, forward_key in _REVERSE_TO_FORWARD:
        if reverse_key in cleaned:
            value = cleaned.pop(reverse_key)
            if _is_configured_value(value):
                reverse_values[forward_key] = value
    return cleaned, reverse_values


def _swap_endpoints(endpoints: dict[str, Any]) -> dict[str, Any]:
    source = endpoints.get(connection.CONF_SOURCE)
    target = endpoints.get(connection.CONF_TARGET)
    return {
        connection.CONF_SOURCE: normalize_connection_target(target),
        connection.CONF_TARGET: normalize_connection_target(source),
    }


def _reverse_connection_name(base_name: str, source_name: str, target_name: str) -> str:
    return f"{base_name} ({target_name} to {source_name})"


def _unique_connection_name(base_name: str, existing_names: set[str]) -> str:
    if base_name not in existing_names:
        return base_name
    suffix = 2
    while f"{base_name} {suffix}" in existing_names:
        suffix += 1
    return f"{base_name} {suffix}"


def migrate_connection_config(
    data: dict[str, Any],
    *,
    existing_names: set[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Migrate a connection config to unidirectional fields.

    Returns:
        Tuple of forward connection data and optional reverse connection data
        when reverse-direction fields were configured.

    """
    migrated = dict(data)
    migrated.pop("segment_order", None)

    reverse_power: dict[str, Any] = {}
    reverse_pricing: dict[str, Any] = {}
    reverse_efficiency: dict[str, Any] = {}

    power_limits, extracted_power = _strip_reverse_from_section(_section_dict(migrated, SECTION_POWER_LIMITS))
    pricing, extracted_pricing = _strip_reverse_from_section(_section_dict(migrated, SECTION_PRICING))
    efficiency, extracted_efficiency = _strip_reverse_from_section(_section_dict(migrated, SECTION_EFFICIENCY))

    reverse_power.update(extracted_power)
    reverse_pricing.update(extracted_pricing)
    reverse_efficiency.update(extracted_efficiency)

    migrated[SECTION_POWER_LIMITS] = power_limits
    migrated[SECTION_PRICING] = pricing
    migrated[SECTION_EFFICIENCY] = efficiency

    has_reverse = bool(reverse_power or reverse_pricing or reverse_efficiency)
    if not has_reverse:
        return migrated, None

    endpoints = _section_dict(migrated, connection.SECTION_ENDPOINTS)
    source_name = get_connection_target_name(endpoints.get(connection.CONF_SOURCE)) or "source"
    target_name = get_connection_target_name(endpoints.get(connection.CONF_TARGET)) or "target"
    base_name = str(migrated.get(CONF_NAME, "Connection"))
    reverse_name = _reverse_connection_name(base_name, source_name, target_name)
    if existing_names is not None:
        reverse_name = _unique_connection_name(reverse_name, existing_names)

    reverse_data: dict[str, Any] = {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: reverse_name,
        connection.SECTION_ENDPOINTS: _swap_endpoints(endpoints),
        SECTION_POWER_LIMITS: reverse_power,
        SECTION_PRICING: reverse_pricing,
        SECTION_EFFICIENCY: reverse_efficiency,
    }
    return migrated, reverse_data


def endpoints_match_reverse(
    endpoints: dict[str, Any],
    *,
    source_name: str,
    target_name: str,
) -> bool:
    """Return True when endpoints are the reverse of the given source/target names."""
    return (
        get_connection_target_name(endpoints.get(connection.CONF_SOURCE)) == target_name
        and get_connection_target_name(endpoints.get(connection.CONF_TARGET)) == source_name
    )


def merge_reverse_into_existing(
    existing: dict[str, Any],
    reverse_data: dict[str, Any],
) -> dict[str, Any]:
    """Merge reverse migration values into an existing reverse connection where unset."""
    merged = dict(existing)
    for section in _REVERSE_SECTIONS:
        existing_section = _section_dict(merged, section)
        reverse_section = _section_dict(reverse_data, section)
        for key, value in reverse_section.items():
            if key not in existing_section or not _is_configured_value(existing_section.get(key)):
                existing_section[key] = value
        merged[section] = existing_section
    return merged


__all__ = [
    "endpoints_match_reverse",
    "merge_reverse_into_existing",
    "migrate_connection_config",
]

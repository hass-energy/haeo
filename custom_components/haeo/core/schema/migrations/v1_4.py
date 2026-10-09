"""Pure config transformation logic for v1.4 connection unidirectional migration."""

from __future__ import annotations

from collections.abc import Mapping

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    get_connection_target_name,
    is_connection_target,
    is_constant_value,
    is_none_value,
    normalize_connection_target,
)
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

REVERSE_TO_FORWARD: tuple[tuple[str, str], ...] = (
    (CONF_MAX_POWER_TARGET_SOURCE, CONF_MAX_POWER_SOURCE_TARGET),
    (CONF_PRICE_TARGET_SOURCE, CONF_PRICE_SOURCE_TARGET),
    (CONF_EFFICIENCY_TARGET_SOURCE, CONF_EFFICIENCY_SOURCE_TARGET),
)

_REVERSE_SECTIONS: tuple[str, ...] = (SECTION_POWER_LIMITS, SECTION_PRICING, SECTION_EFFICIENCY)


def _is_configured_value(value: object) -> bool:
    """Return True when a schema value represents an active configuration."""
    return value is not None and not is_none_value(value)


def endpoint_name(value: object) -> str | None:
    """Return the element name of a stored connection endpoint."""
    if value is None or isinstance(value, str) or is_connection_target(value):
        return get_connection_target_name(value)
    msg = f"Unsupported connection target {value!r}"
    raise TypeError(msg)


def _section_dict(data: Mapping[str, object], section: str) -> dict[str, object]:
    section_data = data.get(section, {})
    return dict(section_data) if isinstance(section_data, dict) else {}


def _strip_reverse_from_section(section_data: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    """Remove reverse-direction keys and return extracted reverse values."""
    reverse_values: dict[str, object] = {}
    cleaned = dict(section_data)
    for reverse_key, forward_key in REVERSE_TO_FORWARD:
        if reverse_key in cleaned:
            value = cleaned.pop(reverse_key)
            if _is_configured_value(value):
                reverse_values[forward_key] = value
    return cleaned, reverse_values


def _swap_endpoints(endpoints: dict[str, object]) -> dict[str, object]:
    return {
        connection.CONF_SOURCE: normalize_connection_target(endpoints[connection.CONF_TARGET]),
        connection.CONF_TARGET: normalize_connection_target(endpoints[connection.CONF_SOURCE]),
    }


def _blocks_reverse_flow(power_limits: dict[str, object]) -> bool:
    """Return True when the legacy reverse max power was the constant 0 used to block reverse flow."""
    value = power_limits.get(CONF_MAX_POWER_TARGET_SOURCE)
    return is_constant_value(value) and value["value"] == 0


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
    data: dict[str, object],
    *,
    existing_names: set[str] | None = None,
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Migrate a connection config to unidirectional fields.

    Since connections became unidirectional in the model, the reverse-direction
    fields have had no effect, so a connection only carried power from source to
    target. A reverse connection is created only when the user set at least one
    reverse-direction field, carrying those fields, so a connection keeps behaving
    as it did unless its reverse settings show reverse flow was intended. A reverse
    max power of the constant 0 blocked reverse flow and creates no reverse connection.

    Returns:
        Tuple of forward connection data and reverse connection data, or None
        when there is no reverse flow to migrate.

    """
    migrated = dict(data)
    migrated.pop("segment_order", None)

    legacy_power_limits = _section_dict(migrated, SECTION_POWER_LIMITS)
    blocks_reverse = _blocks_reverse_flow(legacy_power_limits)

    power_limits, reverse_power = _strip_reverse_from_section(legacy_power_limits)
    pricing, reverse_pricing = _strip_reverse_from_section(_section_dict(migrated, SECTION_PRICING))
    efficiency, reverse_efficiency = _strip_reverse_from_section(_section_dict(migrated, SECTION_EFFICIENCY))

    migrated[SECTION_POWER_LIMITS] = power_limits
    migrated[SECTION_PRICING] = pricing
    migrated[SECTION_EFFICIENCY] = efficiency

    if blocks_reverse or not (reverse_power or reverse_pricing or reverse_efficiency):
        return migrated, None

    endpoints = _section_dict(migrated, connection.SECTION_ENDPOINTS)
    source_name = endpoint_name(endpoints.get(connection.CONF_SOURCE)) or "source"
    target_name = endpoint_name(endpoints.get(connection.CONF_TARGET)) or "target"
    base_name = str(migrated.get(CONF_NAME, "Connection"))
    reverse_name = _reverse_connection_name(base_name, source_name, target_name)
    if existing_names is not None:
        reverse_name = _unique_connection_name(reverse_name, existing_names)

    reverse_data: dict[str, object] = {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: reverse_name,
        connection.SECTION_ENDPOINTS: _swap_endpoints(endpoints),
        SECTION_POWER_LIMITS: reverse_power,
        SECTION_PRICING: reverse_pricing,
        SECTION_EFFICIENCY: reverse_efficiency,
    }
    return migrated, reverse_data


def endpoints_match_reverse(
    endpoints: Mapping[str, object],
    *,
    source_name: str,
    target_name: str,
) -> bool:
    """Return True when endpoints are the reverse of the given source/target names."""
    return (
        endpoint_name(endpoints.get(connection.CONF_SOURCE)) == target_name
        and endpoint_name(endpoints.get(connection.CONF_TARGET)) == source_name
    )


def merge_reverse_into_existing(
    existing: Mapping[str, object],
    reverse_data: Mapping[str, object],
) -> dict[str, object]:
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
    "REVERSE_TO_FORWARD",
    "endpoint_name",
    "endpoints_match_reverse",
    "merge_reverse_into_existing",
    "migrate_connection_config",
]

"""Pure config transformation logic for the v1.4 migration.

Connections become unidirectional, nodes that neither source nor sink power
become junctions, the hub's horizon preset and tiers become a horizon choice,
and battery undercharge and overcharge partitions become reserves and headroom.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from custom_components.haeo.core.const import (
    CONF_ELEMENT_TYPE,
    CONF_HORIZON,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESET_DAYS,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
)
from custom_components.haeo.core.data.loader.config_loader import resolve_field
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import (
    as_constant_value,
    get_connection_target_name,
    is_connection_target,
    is_constant_value,
    is_entity_value,
    is_none_value,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.elements import battery, connection, headroom, junction, node, reserve
from custom_components.haeo.core.schema.field_hints import FieldHint
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
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
from custom_components.haeo.core.state import StateMachine

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
    return dict(section_data) if isinstance(section_data, Mapping) else {}


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


def _unique_name(base_name: str, existing_names: set[str]) -> str:
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
        reverse_name = _unique_name(reverse_name, existing_names)

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


def _role_enabled(value: object) -> bool:
    """Return True when a node role field is on, or driven by an entity that can turn it on."""
    if value is None or value is False or is_none_value(value):
        return False
    if is_constant_value(value):
        return bool(value["value"])
    return True


def node_is_junction(data: Mapping[str, object]) -> bool:
    """Return True when a node config neither sources nor sinks power."""
    role = data.get(node.SECTION_ROLE)
    if not isinstance(role, Mapping):
        return True
    return not any(_role_enabled(role.get(field)) for field in (node.CONF_IS_SOURCE, node.CONF_IS_SINK))


def junction_config(data: Mapping[str, object]) -> dict[str, object]:
    """Return the junction config that replaces a node config."""
    return {CONF_ELEMENT_TYPE: junction.ELEMENT_TYPE, CONF_NAME: data[CONF_NAME]}


def migrate_hub_horizon(data: Mapping[str, object]) -> dict[str, object]:
    """Replace the hub's horizon preset and tiers with a horizon choice holding the preset.

    Custom tiers are no longer supported, so a hub using them gets the default preset.
    """
    migrated = {key: value for key, value in data.items() if key != HUB_SECTION_TIERS}
    common = _section_dict(data, HUB_SECTION_COMMON)
    preset = common.pop(CONF_HORIZON_PRESET, None)
    common[CONF_HORIZON] = as_horizon_preset_value(
        preset if isinstance(preset, str) and preset in HORIZON_PRESET_DAYS else HORIZON_PRESET_5_DAYS
    )
    migrated[HUB_SECTION_COMMON] = common
    return migrated


type ValueResolver = Callable[[object, OutputType], float | None]
"""Read a stored schema value as a number, with percentages as ratios, or None when it has none."""

# Window of the requirements partitions become. They cover no loads or
# generation, so the window does not change what they hold.
PARTITION_REQUIREMENT_WINDOW = 1.0


def state_value_resolver(sm: StateMachine) -> ValueResolver:
    """Return a resolver reading constants as stored and entities from their current state."""

    def resolve(value: object, output_type: OutputType) -> float | None:
        if not (is_constant_value(value) or is_entity_value(value)):
            return None
        resolved = resolve_field(value, FieldHint(output_type=output_type), sm, ())
        return resolved if isinstance(resolved, float) else None

    return resolve


@dataclass(frozen=True, slots=True)
class BatteryPartitionMigration:
    """A battery config without partitions, and the requirements that replace them.

    Attributes:
        battery: The battery config with its partition sections removed.
        requirements: Reserve and headroom configs holding what the partitions priced.
        unconverted: Partition sections whose values could not be read, so they were dropped.

    """

    battery: dict[str, object]
    requirements: tuple[dict[str, object], ...]
    unconverted: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _PartitionKind:
    section: str
    limit_key: str
    default_limit: float
    efficiency_key: str
    element_type: str
    suffix: str


_PARTITION_KINDS: tuple[_PartitionKind, ...] = (
    _PartitionKind(
        section=partitions.SECTION_UNDERCHARGE,
        limit_key=battery.CONF_MIN_CHARGE_PERCENTAGE,
        default_limit=0.0,
        efficiency_key=CONF_EFFICIENCY_SOURCE_TARGET,
        element_type=reserve.ELEMENT_TYPE,
        suffix="reserve",
    ),
    _PartitionKind(
        section=partitions.SECTION_OVERCHARGE,
        limit_key=battery.CONF_MAX_CHARGE_PERCENTAGE,
        default_limit=1.0,
        efficiency_key=CONF_EFFICIENCY_TARGET_SOURCE,
        element_type=headroom.ELEMENT_TYPE,
        suffix="headroom",
    ),
)

_PARTITION_SECTIONS: frozenset[str] = frozenset(
    (partitions.SECTION_PARTITIONING, partitions.SECTION_UNDERCHARGE, partitions.SECTION_OVERCHARGE)
)


def _requirement(
    kind: _PartitionKind,
    data: Mapping[str, object],
    resolve: ValueResolver,
) -> tuple[object, dict[str, object] | None] | None:
    """Return the battery limit and requirement that replace one partition.

    A partition let the battery go past its limit to the partition percentage,
    charging a holding cost for each kWh past the limit. The partition
    percentage becomes the limit, and a requirement holds the energy between
    the two, measured as the battery delivers it (an undercharge reserve) or
    takes it in (overcharge headroom). Its cost per kWh of shortfall is scaled
    by the same efficiency, so every plan costs what it did.

    Returns:
        None when the partition is not priced. Otherwise the new limit and the
        requirement, or no requirement when the partition holds no energy.

    Raises:
        ValueError: If a value the conversion needs cannot be read.

    """
    partition = _section_dict(data, kind.section)
    percentage = partition.get(partitions.CONF_PARTITION_PERCENTAGE)
    cost = partition.get(partitions.CONF_PARTITION_COST)
    if not (_is_configured_value(percentage) and _is_configured_value(cost)):
        return None

    def read(value: object, output_type: OutputType, default: float | None = None) -> float:
        if default is not None and not _is_configured_value(value):
            return default
        resolved = resolve(value, output_type)
        if resolved is None:
            msg = f"{kind.section} needs a value for {value!r}"
            raise ValueError(msg)
        return resolved

    limits = _section_dict(data, battery.SECTION_LIMITS)
    storage = _section_dict(data, battery.SECTION_STORAGE)
    efficiency_value = _section_dict(data, SECTION_EFFICIENCY).get(kind.efficiency_key)
    efficiency = read(efficiency_value, OutputType.EFFICIENCY, 1.0)

    limit = read(limits.get(kind.limit_key), OutputType.STATE_OF_CHARGE, kind.default_limit)
    past_limit = read(percentage, OutputType.STATE_OF_CHARGE)
    is_reserve = kind.element_type == reserve.ELEMENT_TYPE
    held = (limit - past_limit if is_reserve else past_limit - limit) * read(
        storage.get(battery.CONF_CAPACITY), OutputType.ENERGY
    )
    if held <= 0:
        return percentage, None

    if is_reserve:
        minimum, cost_scale = held * efficiency, 1.0 / efficiency
    else:
        minimum, cost_scale = held / efficiency, efficiency
    shortfall_cost = cost if cost_scale == 1.0 else as_constant_value(read(cost, OutputType.PRICE_RATE) * cost_scale)

    requirement: dict[str, object] = {
        CONF_ELEMENT_TYPE: kind.element_type,
        CONF_NAME: f"{data[CONF_NAME]} {kind.suffix}",
        reserve.SECTION_PARTICIPANTS: {reserve.CONF_STORAGE: [data[CONF_NAME]]},
        reserve.SECTION_REQUIREMENT: {
            reserve.CONF_WINDOW: as_constant_value(PARTITION_REQUIREMENT_WINDOW),
            reserve.CONF_MINIMUM: as_constant_value(round(minimum, 9)),
        },
        reserve.SECTION_PRICING: {reserve.CONF_SHORTFALL_COST: shortfall_cost},
    }
    return percentage, requirement


def migrate_battery_partitions(
    data: Mapping[str, object],
    resolve: ValueResolver,
    *,
    existing_names: set[str],
) -> BatteryPartitionMigration:
    """Replace a battery's undercharge and overcharge partitions with a reserve and headroom.

    Requirement names are made unique against ``existing_names``, which gains each new name.
    A partition whose values cannot be read is dropped, leaving the battery's limit as it was.
    """
    migrated = {key: value for key, value in data.items() if key not in _PARTITION_SECTIONS}
    limits = _section_dict(data, battery.SECTION_LIMITS)
    requirements: list[dict[str, object]] = []
    unconverted: list[str] = []

    for kind in _PARTITION_KINDS:
        try:
            converted = _requirement(kind, data, resolve)
        except ValueError:
            unconverted.append(kind.section)
            continue
        if converted is None:
            continue
        limit, requirement = converted
        limits[kind.limit_key] = limit
        if requirement is not None:
            name = _unique_name(str(requirement[CONF_NAME]), existing_names)
            existing_names.add(name)
            requirement[CONF_NAME] = name
            requirements.append(requirement)

    migrated[battery.SECTION_LIMITS] = limits
    return BatteryPartitionMigration(migrated, tuple(requirements), tuple(unconverted))


__all__ = [
    "PARTITION_REQUIREMENT_WINDOW",
    "REVERSE_TO_FORWARD",
    "BatteryPartitionMigration",
    "ValueResolver",
    "endpoint_name",
    "endpoints_match_reverse",
    "junction_config",
    "merge_reverse_into_existing",
    "migrate_battery_partitions",
    "migrate_connection_config",
    "migrate_hub_horizon",
    "node_is_junction",
    "state_value_resolver",
]

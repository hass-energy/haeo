"""Pure config transformation logic for the v1.4 migration.

Connections become unidirectional, nodes that neither source nor sink power
become junctions, the hub's horizon preset and tiers become a horizon choice,
and battery undercharge and overcharge partitions become buffers.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
import logging

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
from custom_components.haeo.core.schema import (
    as_connection_target,
    as_constant_value,
    extract_connection_target,
    is_constant_value,
    is_none_value,
    normalize_connection_target,
)
from custom_components.haeo.core.schema.elements import battery, buffer, connection, junction, node
from custom_components.haeo.core.schema.horizon_value import as_horizon_preset_value
from custom_components.haeo.core.schema.migrations import battery_partitions as partitions
from custom_components.haeo.core.schema.migrations import section_dict
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

_LOGGER = logging.getLogger(__name__)

# The config entry minor version these migrations bring an entry to
MINOR_VERSION = 4

# Each reverse-direction connection field, with its section and the field
# that holds the same setting on a connection running the other way
REVERSE_FIELDS: Mapping[str, tuple[str, str]] = {
    CONF_MAX_POWER_TARGET_SOURCE: (SECTION_POWER_LIMITS, CONF_MAX_POWER_SOURCE_TARGET),
    CONF_PRICE_TARGET_SOURCE: (SECTION_PRICING, CONF_PRICE_SOURCE_TARGET),
    CONF_EFFICIENCY_TARGET_SOURCE: (SECTION_EFFICIENCY, CONF_EFFICIENCY_SOURCE_TARGET),
}

_CONNECTION_SECTIONS: tuple[str, ...] = (SECTION_POWER_LIMITS, SECTION_PRICING, SECTION_EFFICIENCY)

_SEGMENT_ORDER = "segment_order"

# The name the hub's Switchboard node was created with. English is the only
# language HAEO has shipped translations for, and Home Assistant falls back to
# it, so every Switchboard got this name whatever the language.
SWITCHBOARD_NAME = "Switchboard"


def _is_configured_value(value: object) -> bool:
    """Return True when a schema value represents an active configuration."""
    return value is not None and not is_none_value(value)


def _blocks_reverse_flow(value: object) -> bool:
    """Return True when a legacy reverse max power is the constant 0 used to block reverse flow."""
    return is_constant_value(value) and value["value"] == 0


def _unique_name(base_name: str, existing_names: set[str]) -> str:
    if base_name not in existing_names:
        return base_name
    suffix = 2
    while f"{base_name} {suffix}" in existing_names:
        suffix += 1
    return f"{base_name} {suffix}"


def connection_route(data: Mapping[str, object]) -> tuple[str, str]:
    """Return the names of the elements a connection carries power from and to."""
    endpoints = section_dict(data, connection.SECTION_ENDPOINTS)
    return (
        extract_connection_target(normalize_connection_target(endpoints[connection.CONF_SOURCE])),
        extract_connection_target(normalize_connection_target(endpoints[connection.CONF_TARGET])),
    )


def migrate_connection_config(
    data: Mapping[str, object],
    *,
    existing_names: set[str],
    routes: AbstractSet[tuple[str, str]],
) -> tuple[dict[str, object], dict[str, object] | None]:
    """Migrate a connection config to unidirectional fields.

    Since connections became unidirectional in the model, the reverse-direction
    fields have had no effect, so a connection only carried power from source to
    target. The reverse fields are removed, and a reverse connection carrying
    them is created only when they show reverse flow was intended: at least one
    is set, the reverse max power is not the constant 0 that blocked reverse
    flow, and no other connection already carries power the other way. A
    connection that already does keeps behaving as it did.

    ``routes`` holds the (source, target) names of every connection from
    before the migration, see ``connection_route``, so reverse connections the
    migration creates do not count. The reverse connection's name is made
    unique against ``existing_names``, which gains it.

    Returns:
        Tuple of forward connection data and reverse connection data, or None
        when there is no reverse flow to migrate.

    """
    name = str(data[CONF_NAME])
    sections = {section: section_dict(data, section) for section in _CONNECTION_SECTIONS}
    reverse_values = {
        key: value
        for key, (section, _) in REVERSE_FIELDS.items()
        if _is_configured_value(value := sections[section].pop(key, None))
    }
    forward = {key: value for key, value in data.items() if key != _SEGMENT_ORDER} | sections
    if not reverse_values:
        return forward, None

    dropped = ", ".join(reverse_values)

    if _blocks_reverse_flow(reverse_values.get(CONF_MAX_POWER_TARGET_SOURCE)):
        _LOGGER.info(
            "Connection %s blocked reverse flow with a max power of 0, so no reverse connection was created "
            "and its reverse settings were dropped: %s",
            name,
            dropped,
        )
        return forward, None

    source_name, target_name = connection_route(data)
    if source_name != target_name and (target_name, source_name) in routes:
        _LOGGER.info(
            "Another connection already carries power from %s to %s, so connection %s keeps carrying power "
            "one way and its reverse settings, which had no effect, were dropped: %s",
            target_name,
            source_name,
            name,
            dropped,
        )
        return forward, None

    reverse_name = _unique_name(f"{name} ({target_name} to {source_name})", existing_names)
    existing_names.add(reverse_name)
    reverse: dict[str, object] = {
        CONF_ELEMENT_TYPE: connection.ELEMENT_TYPE,
        CONF_NAME: reverse_name,
        connection.SECTION_ENDPOINTS: {
            connection.CONF_SOURCE: as_connection_target(target_name),
            connection.CONF_TARGET: as_connection_target(source_name),
        },
    }
    reverse_sections: dict[str, dict[str, object]] = {section: {} for section in _CONNECTION_SECTIONS}
    for key, value in reverse_values.items():
        section, forward_key = REVERSE_FIELDS[key]
        reverse_sections[section][forward_key] = value
    reverse.update(reverse_sections)
    return forward, reverse


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


def node_becomes_junction(name: str, data: Mapping[str, object], *, advanced_mode: bool) -> bool:
    """Return True when the node called ``name`` is replaced by a junction.

    The Switchboard is always a junction. Outside advanced mode a node cannot be
    configured, so every node becomes a junction. In advanced mode, other nodes
    become junctions only when neither their source nor sink switch is on.
    """
    return node_is_junction(data) or not advanced_mode or name == SWITCHBOARD_NAME


def junction_config(data: Mapping[str, object]) -> dict[str, object]:
    """Return the junction config that replaces a node config."""
    return {CONF_ELEMENT_TYPE: junction.ELEMENT_TYPE, CONF_NAME: data[CONF_NAME]}


@dataclass(frozen=True, slots=True)
class HubHorizonMigration:
    """A migrated hub config.

    Attributes:
        hub: The hub config with a horizon choice in place of its preset and tiers.
        tiers_replaced_by: The preset that replaced the hub's custom tiers, or
            None when the hub kept its horizon.

    """

    hub: dict[str, object]
    tiers_replaced_by: str | None


def migrate_hub_horizon(data: Mapping[str, object]) -> HubHorizonMigration:
    """Replace the hub's horizon preset and tiers with a horizon choice holding the preset.

    A hub that already has a horizon choice keeps it. Custom tiers are no
    longer supported, so a hub using them gets the default preset.
    """
    migrated = {key: value for key, value in data.items() if key != HUB_SECTION_TIERS}
    common = section_dict(data, HUB_SECTION_COMMON)
    preset = common.pop(CONF_HORIZON_PRESET, None)
    tiers_replaced_by: str | None = None
    if CONF_HORIZON not in common:
        if isinstance(preset, str) and preset in HORIZON_PRESET_DAYS:
            common[CONF_HORIZON] = as_horizon_preset_value(preset)
        else:
            common[CONF_HORIZON] = as_horizon_preset_value(HORIZON_PRESET_5_DAYS)
            tiers_replaced_by = None if preset is None else HORIZON_PRESET_5_DAYS
    migrated[HUB_SECTION_COMMON] = common
    return HubHorizonMigration(migrated, tiers_replaced_by)


# Window of the buffers partitions become. They cover no loads or generation,
# so the window does not change what they hold.
PARTITION_BUFFER_WINDOW = 1.0

# The cost batteries held their min and max charge with before it was configurable
LEGACY_CHARGE_LIMIT_COST = 100.0


@dataclass(frozen=True, slots=True)
class BatteryMigration:
    """A migrated battery config, and the buffers that replace its partitions.

    Attributes:
        battery: The battery config without partitions and with its advanced section.
        buffers: Buffer configs holding what the partitions priced.

    """

    battery: dict[str, object]
    buffers: tuple[dict[str, object], ...]


@dataclass(frozen=True, slots=True)
class _PartitionKind:
    section: str
    limit_key: str
    kind: buffer.BufferKind


_PARTITION_KINDS: tuple[_PartitionKind, ...] = (
    _PartitionKind(partitions.SECTION_UNDERCHARGE, battery.CONF_MIN_CHARGE_PERCENTAGE, buffer.KIND_RESERVE),
    _PartitionKind(partitions.SECTION_OVERCHARGE, battery.CONF_MAX_CHARGE_PERCENTAGE, buffer.KIND_HEADROOM),
)

_PARTITION_SECTIONS: frozenset[str] = frozenset(
    (partitions.SECTION_PARTITIONING, partitions.SECTION_UNDERCHARGE, partitions.SECTION_OVERCHARGE)
)


def migrate_battery_config(data: Mapping[str, object], *, existing_names: set[str]) -> BatteryMigration:
    """Replace a battery's partitions with buffers and add the cost of its charge limits.

    The battery's advanced section gets the limit cost its min and max charge
    were held with before it was configurable.

    A partition let the battery go past its limit to the partition percentage,
    charging a holding cost for each kWh stored past the limit. The partition
    percentage becomes the battery's limit, and a buffer for the battery takes
    the old limit as its level and the partition cost as its shortfall cost,
    so every plan costs what it did. Values move across as they are, sensors
    included. A partition past an unset limit priced nothing, so it only moves
    the limit.

    Buffer names are made unique against ``existing_names``, which gains each new name.
    """
    migrated = {key: value for key, value in data.items() if key not in _PARTITION_SECTIONS}
    limits = section_dict(data, battery.SECTION_LIMITS)
    buffers: list[dict[str, object]] = []
    battery_name = str(data[CONF_NAME])

    for kind in _PARTITION_KINDS:
        partition = section_dict(data, kind.section)
        percentage = partition.get(partitions.CONF_PARTITION_PERCENTAGE)
        cost = partition.get(partitions.CONF_PARTITION_COST)
        if not (_is_configured_value(percentage) and _is_configured_value(cost)):
            continue
        old_limit = limits.get(kind.limit_key)
        limits[kind.limit_key] = percentage
        if not _is_configured_value(old_limit):
            continue
        name = _unique_name(f"{battery_name} {kind.kind}", existing_names)
        existing_names.add(name)
        buffers.append(
            {
                CONF_ELEMENT_TYPE: buffer.ELEMENT_TYPE,
                CONF_NAME: name,
                buffer.CONF_KIND: kind.kind,
                buffer.SECTION_PARTICIPANTS: {buffer.CONF_STORAGE: [battery_name]},
                buffer.SECTION_REQUIREMENT: {
                    buffer.CONF_WINDOW: as_constant_value(PARTITION_BUFFER_WINDOW),
                    buffer.CONF_LEVEL: old_limit,
                },
                buffer.SECTION_PRICING: {buffer.CONF_SHORTFALL_COST: cost},
            }
        )

    migrated[battery.SECTION_LIMITS] = limits
    migrated[battery.SECTION_ADVANCED] = {
        battery.CONF_CHARGE_LIMIT_COST: as_constant_value(LEGACY_CHARGE_LIMIT_COST),
        **section_dict(data, battery.SECTION_ADVANCED),
    }
    return BatteryMigration(migrated, tuple(buffers))


@dataclass(frozen=True)
class ParticipantMigration:
    """Element configs after the v1.4 element migrations.

    Attributes:
        participants: Every element's config by name. Elements the migration
            created follow the elements they came from.
        created_from: The name of the element each created element came from.
        junctions: The names of nodes replaced by junctions.

    """

    participants: dict[str, dict[str, object]]
    created_from: dict[str, str]
    junctions: tuple[str, ...]


def migrate_participants(
    participants: Mapping[str, Mapping[str, object]], *, advanced_mode: bool
) -> ParticipantMigration:
    """Apply the v1.4 element migrations to element configs keyed by name.

    Every connection becomes unidirectional first, then every battery moves its
    partitions into buffers, then nodes that only pass power through become
    junctions. Each step runs over every element before the next starts, so
    created elements are named in the same order whoever applies the result.
    The steps are for configs older than v1.4: a current node that sources or
    sinks power becomes a junction outside advanced mode.
    """
    existing_names = set(participants)
    routes = {
        connection_route(config)
        for config in participants.values()
        if config[CONF_ELEMENT_TYPE] == connection.ELEMENT_TYPE
    }
    created_from: dict[str, str] = {}
    added: dict[str, list[tuple[str, dict[str, object]]]] = {name: [] for name in participants}
    migrated = {name: dict(config) for name, config in participants.items()}

    for name, config in participants.items():
        if config[CONF_ELEMENT_TYPE] == connection.ELEMENT_TYPE:
            forward, reverse = migrate_connection_config(config, existing_names=existing_names, routes=routes)
            migrated[name] = forward
            if reverse is not None:
                added[name].append((str(reverse[CONF_NAME]), reverse))

    for name, config in participants.items():
        if config[CONF_ELEMENT_TYPE] == battery.ELEMENT_TYPE:
            migration = migrate_battery_config(config, existing_names=existing_names)
            migrated[name] = migration.battery
            added[name].extend((str(buffer_config[CONF_NAME]), buffer_config) for buffer_config in migration.buffers)

    junctions = tuple(
        name
        for name, config in participants.items()
        if config[CONF_ELEMENT_TYPE] == node.ELEMENT_TYPE
        and node_becomes_junction(name, config, advanced_mode=advanced_mode)
    )
    for name in junctions:
        migrated[name] = junction_config(participants[name])

    ordered: dict[str, dict[str, object]] = {}
    for name, config in migrated.items():
        ordered[name] = config
        for created_name, created_config in added[name]:
            ordered[created_name] = created_config
            created_from[created_name] = name
    return ParticipantMigration(ordered, created_from, junctions)


__all__ = [
    "LEGACY_CHARGE_LIMIT_COST",
    "MINOR_VERSION",
    "PARTITION_BUFFER_WINDOW",
    "REVERSE_FIELDS",
    "SWITCHBOARD_NAME",
    "BatteryMigration",
    "HubHorizonMigration",
    "ParticipantMigration",
    "connection_route",
    "junction_config",
    "migrate_battery_config",
    "migrate_connection_config",
    "migrate_hub_horizon",
    "migrate_participants",
    "node_becomes_junction",
    "node_is_junction",
]

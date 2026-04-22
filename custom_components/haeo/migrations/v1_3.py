"""Migration helpers for config entry version 1.3."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.migrations.v1_3 import migrate_element_config, migrate_hub_config
from custom_components.haeo.core.schema.sections import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
)

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 3
_BATTERY_TYPE = "battery"
_SOLAR_TYPE = "solar"
_LOAD_TYPE = "load"
_CONNECTION_TYPE = "connection"
_POLICY_TYPE = "policy"
_NONE_VALUE: dict[str, str] = {"type": "none"}
_POLICIES_TITLE = "Policies"
# Pre-v0.4 leaf field names that must be renamed to their directional
# (source/target) equivalents during the v1.3 entity-uid migration. The data
# side of these renames is handled in `core.schema.migrations.v1_3`; this map
# lets the entity registry catch up so existing entities keep their entity_id
# instead of getting `_2` suffixes when the new platform creates new uids.
_FIELD_RENAMES_BY_ELEMENT_TYPE: dict[str, dict[str, str]] = {
    "grid": {
        "import_price": CONF_PRICE_SOURCE_TARGET,
        "export_price": CONF_PRICE_TARGET_SOURCE,
        "import_limit": CONF_MAX_POWER_SOURCE_TARGET,
        "export_limit": CONF_MAX_POWER_TARGET_SOURCE,
    },
    "inverter": {
        "max_power_dc_to_ac": CONF_MAX_POWER_SOURCE_TARGET,
        "max_power_ac_to_dc": CONF_MAX_POWER_TARGET_SOURCE,
        "efficiency_dc_to_ac": CONF_EFFICIENCY_SOURCE_TARGET,
        "efficiency_ac_to_dc": CONF_EFFICIENCY_TARGET_SOURCE,
    },
    "battery": {
        # Sides intentionally swap: charging the battery is power flowing
        # `target -> source` from the battery's perspective; discharging is
        # `source -> target`. Matches the data-side mapping in
        # core.schema.migrations.v1_3._migrate_element_to_sectioned (battery).
        "max_charge_power": CONF_MAX_POWER_TARGET_SOURCE,
        "max_discharge_power": CONF_MAX_POWER_SOURCE_TARGET,
    },
}
_DEFAULT_POLICY_PRICES: dict[tuple[str, str], frozenset[float]] = {
    (_BATTERY_TYPE, CONF_PRICE_SOURCE_TARGET): frozenset({0.0}),
    # 0.001 was the legacy early-charge-incentive default; we migrate it
    # through to a real -$0.001/kWh "*→Battery" policy rather than dropping
    # it, because the new optimizer has no implicit early-charge behaviour
    # and silently discarding the value would change existing installs'
    # charging preference (they'd stop pulling free upstream power into
    # storage when export is unprofitable).
    (_BATTERY_TYPE, CONF_PRICE_TARGET_SOURCE): frozenset({0.0, 0.01}),
    (_SOLAR_TYPE, CONF_PRICE_SOURCE_TARGET): frozenset({0.0}),
}
UNIQUE_ID_PART_COUNT = 3
LIST_ITEM_PATH_PART_COUNT = 3


def migrate_subentry_data(subentry: ConfigSubentry) -> dict[str, Any] | None:
    """Migrate a subentry's data to sectioned config if needed."""
    return migrate_element_config(dict(subentry.data))


def _policy_subentry(*, rules: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "element_type": _POLICY_TYPE,
        "name": _POLICIES_TITLE,
        CONF_RULES: rules,
    }


def _negate_price_value(price: dict[str, Any]) -> dict[str, Any]:
    if price.get("type") == "constant":
        return {**price, "value": -price["value"]}
    _LOGGER.warning(
        "Cannot negate non-constant charge price during migration; "
        "a positive entity price will behave as a cost in the new policy system. "
        "To preserve incentive semantics, use a template sensor that outputs a negated value: %s",
        price,
    )
    return price


def _is_default_policy_price(element_type: str, field_name: str, price: Any) -> bool:
    """Return True when a constant price matches a legacy default value."""
    defaults = _DEFAULT_POLICY_PRICES.get((element_type, field_name))
    if defaults is None:
        return False
    if not isinstance(price, dict) or price.get("type") != "constant":
        return False
    value = price.get("value")
    if not isinstance(value, (int, float)):
        return False
    return float(value) in defaults


def _extract_pricing_rules(data: dict[str, Any], subentry: ConfigSubentry) -> list[dict[str, Any]]:
    element_type = data.get("element_type")
    element_name = data.get("name", subentry.title)
    pricing = data.get("pricing", {})
    if not isinstance(pricing, dict):
        pricing = {}
    rules: list[dict[str, Any]] = []

    if element_type == _BATTERY_TYPE:
        discharge_price = pricing.get(CONF_PRICE_SOURCE_TARGET)
        if discharge_price is not None and not _is_default_policy_price(
            _BATTERY_TYPE,
            CONF_PRICE_SOURCE_TARGET,
            discharge_price,
        ):
            rules.append(
                {
                    "name": f"{element_name} Discharge",
                    "enabled": True,
                    "source": [element_name],
                    "price": discharge_price,
                }
            )

        charge_price = pricing.get(CONF_PRICE_TARGET_SOURCE)
        if charge_price is not None and not _is_default_policy_price(
            _BATTERY_TYPE,
            CONF_PRICE_TARGET_SOURCE,
            charge_price,
        ):
            rules.append(
                {
                    "name": f"{element_name} Charge",
                    "enabled": True,
                    "target": [element_name],
                    "price": _negate_price_value(charge_price),
                }
            )
    elif element_type == _SOLAR_TYPE:
        price_st = pricing.get(CONF_PRICE_SOURCE_TARGET)
        if price_st is not None and not _is_default_policy_price(
            _SOLAR_TYPE,
            CONF_PRICE_SOURCE_TARGET,
            price_st,
        ):
            rules.append(
                {
                    "name": f"{element_name} Production",
                    "enabled": True,
                    "source": [element_name],
                    "price": price_st,
                }
            )

    return [rule for rule in rules if rule.get("price") != _NONE_VALUE]


def _strip_pricing_from_battery(data: dict[str, Any]) -> dict[str, Any]:
    pricing = dict(data.get("pricing", {})) if isinstance(data.get("pricing"), dict) else {}
    pricing.pop(CONF_PRICE_SOURCE_TARGET, None)
    pricing.pop(CONF_PRICE_TARGET_SOURCE, None)
    data["pricing"] = pricing
    return data


def _strip_pricing_from_solar(data: dict[str, Any]) -> dict[str, Any]:
    data.pop("pricing", None)
    return data


def _strip_pricing_from_load(data: dict[str, Any]) -> dict[str, Any]:
    data.pop("pricing", None)
    return data


async def _migrate_entity_unique_ids(hass: HomeAssistant, entry: ConfigEntry) -> None:
    registry = er.async_get(hass)
    candidate_unique_ids: dict[str, str] = {}
    candidate_counts: dict[str, int] = {}

    subentry_types: dict[str, str] = {sid: sub.subentry_type or "" for sid, sub in entry.subentries.items()}

    for entity_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
        uid = entity_entry.unique_id
        if not uid:
            continue

        parts = uid.split("_", 2)
        if len(parts) != UNIQUE_ID_PART_COUNT:
            continue

        subentry_id = parts[1]
        field_path_key = parts[2]
        path_parts = field_path_key.split(".")
        if len(path_parts) >= LIST_ITEM_PATH_PART_COUNT:
            continue

        new_leaf = path_parts[-1]
        renames = _FIELD_RENAMES_BY_ELEMENT_TYPE.get(subentry_types.get(subentry_id, ""), {})
        new_leaf = renames.get(new_leaf, new_leaf)

        new_uid = f"{parts[0]}_{subentry_id}_{new_leaf}"
        if new_uid == uid:
            continue

        candidate_unique_ids[entity_entry.entity_id] = new_uid
        candidate_counts[new_uid] = candidate_counts.get(new_uid, 0) + 1

    def _migrate_unique_id(entity_entry: er.RegistryEntry) -> dict[str, Any] | None:
        new_uid = candidate_unique_ids.get(entity_entry.entity_id)
        if new_uid is None:
            return None

        if candidate_counts.get(new_uid, 0) > 1:
            _LOGGER.info(
                "Skipping unique_id migration for %s because stripped key would collide: %s",
                entity_entry.entity_id,
                new_uid,
            )
            return None

        conflict_entity_id = registry.async_get_entity_id(
            entity_entry.domain,
            entity_entry.platform,
            new_uid,
        )
        if conflict_entity_id and conflict_entity_id != entity_entry.entity_id:
            _LOGGER.info(
                "Removing duplicate entity %s to keep existing stable unique_id %s",
                entity_entry.entity_id,
                new_uid,
            )
            registry.async_remove(entity_entry.entity_id)
            return None

        return {"new_unique_id": new_uid}

    await er.async_migrate_entries(hass, entry.entry_id, _migrate_unique_id)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.3."""
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    new_data, new_options = migrate_hub_config(dict(entry.data), dict(entry.options), entry.title)
    hass.config_entries.async_update_entry(
        entry,
        data=new_data,
        options=new_options,
    )

    new_rules: list[dict[str, Any]] = []
    subentries_to_update: list[tuple[ConfigSubentry, dict[str, Any]]] = []
    existing_policy_subentry: ConfigSubentry | None = None

    for subentry in entry.subentries.values():
        migrated = migrate_subentry_data(subentry)
        data = migrated if migrated is not None else dict(subentry.data)
        if migrated is not None:
            hass.config_entries.async_update_subentry(entry, subentry, data=migrated)
        element_type = data.get("element_type")
        if element_type == _POLICY_TYPE and existing_policy_subentry is None:
            existing_policy_subentry = subentry
            continue
        if element_type == _BATTERY_TYPE:
            new_rules.extend(_extract_pricing_rules(data, subentry))
            subentries_to_update.append((subentry, _strip_pricing_from_battery(data)))
        elif element_type == _SOLAR_TYPE:
            new_rules.extend(_extract_pricing_rules(data, subentry))
            subentries_to_update.append((subentry, _strip_pricing_from_solar(data)))
        elif element_type == _LOAD_TYPE:
            subentries_to_update.append((subentry, _strip_pricing_from_load(data)))
        elif element_type == _CONNECTION_TYPE:
            subentries_to_update.append((subentry, data))

    for subentry, stripped_data in subentries_to_update:
        hass.config_entries.async_update_subentry(entry, subentry, data=stripped_data)

    if new_rules:
        existing_rules: list[dict[str, Any]] = []
        if existing_policy_subentry is not None:
            existing_rules = list(existing_policy_subentry.data.get(CONF_RULES, []))
            hass.config_entries.async_update_subentry(
                entry,
                existing_policy_subentry,
                data=_policy_subentry(rules=[*existing_rules, *new_rules]),
            )
        else:
            hass.config_entries.async_add_subentry(
                entry,
                ConfigSubentry(
                    data=MappingProxyType(_policy_subentry(rules=new_rules)),
                    subentry_type=_POLICY_TYPE,
                    title=_POLICIES_TITLE,
                    unique_id=None,
                ),
            )

    await _migrate_entity_unique_ids(hass, entry)
    hass.config_entries.async_update_entry(entry, minor_version=MINOR_VERSION)
    _LOGGER.info("Migration complete for %s entry %s", DOMAIN, entry.entry_id)
    return True

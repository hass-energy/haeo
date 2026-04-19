"""Migration helpers for config entry version 1.4.

Migrates internal pricing from battery and solar elements to power policy subentries.

Battery:
- price_source_target (discharge wear) -> policy: Battery -> *: $X/kWh
- price_target_source (charge incentive) -> policy: * -> Battery: $X/kWh
- Legacy top-level discharge_cost / early_charge_incentive (pre-v1.3 layout) are migrated the same way

Solar:
- price_source_target (production cost) -> policy: Solar -> *: $X/kWh
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.elements.policy import CONF_RULES
from custom_components.haeo.core.schema.sections import CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4

# Element types that have pricing to migrate
_BATTERY_TYPE = "battery"
_SOLAR_TYPE = "solar"
_LOAD_TYPE = "load"
_CONNECTION_TYPE = "connection"
_POLICY_TYPE = "policy"

_NONE_VALUE: dict[str, str] = {"type": "none"}
_POLICIES_TITLE = "Policies"


def _policy_subentry(*, rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Build stored policy subentry data matching PolicyConfigSchema."""
    return {
        "element_type": _POLICY_TYPE,
        "name": _POLICIES_TITLE,
        CONF_RULES: rules,
    }


def _negate_price_value(price: dict[str, Any]) -> dict[str, Any]:
    """Negate a constant price value for charge incentive migration.

    The old battery adapter produced a negative incentive internally. The new
    policy system uses ``power * price * period`` where positive = cost, so the
    stored positive value must be negated to preserve the original incentive
    semantics.
    """
    if price.get("type") == "constant":
        return {**price, "value": -price["value"]}
    _LOGGER.warning(
        "Cannot negate non-constant charge price during migration; "
        "a positive entity price will behave as a cost in the new policy system. "
        "To preserve incentive semantics, use a template sensor that outputs a negated value: %s",
        price,
    )
    return price


def _extract_pricing_rules(subentry: ConfigSubentry) -> list[dict[str, Any]]:
    """Extract policy rules from an element's pricing section."""
    data = dict(subentry.data)
    element_type = data.get("element_type")
    element_name = data.get("name", subentry.title)
    pricing = data.get("pricing", {})
    if not isinstance(pricing, dict):
        pricing = {}
    rules: list[dict[str, Any]] = []

    if element_type == _BATTERY_TYPE:
        discharge_price = pricing.get(CONF_PRICE_SOURCE_TARGET)
        if discharge_price is not None:
            rules.append(
                {
                    "name": f"{element_name} Discharge",
                    "enabled": True,
                    "source": [element_name],
                    "price": discharge_price,
                },
            )

        charge_price = pricing.get(CONF_PRICE_TARGET_SOURCE)
        if charge_price is not None:
            rules.append(
                {
                    "name": f"{element_name} Charge",
                    "enabled": True,
                    "target": [element_name],
                    "price": _negate_price_value(charge_price),
                },
            )

    elif element_type == _SOLAR_TYPE:
        price_st = pricing.get(CONF_PRICE_SOURCE_TARGET)
        if price_st is not None:
            rules.append(
                {
                    "name": f"{element_name} Production",
                    "enabled": True,
                    "source": [element_name],
                    "price": price_st,
                },
            )

    return [rule for rule in rules if rule.get("price") != _NONE_VALUE]


def _strip_pricing_from_battery(data: dict[str, Any]) -> dict[str, Any]:
    """Remove migrated battery pricing from the pricing section."""
    pricing = dict(data.get("pricing", {})) if isinstance(data.get("pricing"), dict) else {}
    pricing.pop(CONF_PRICE_SOURCE_TARGET, None)
    pricing.pop(CONF_PRICE_TARGET_SOURCE, None)
    data["pricing"] = pricing
    return data


def _strip_pricing_from_solar(data: dict[str, Any]) -> dict[str, Any]:
    """Remove pricing section from solar config."""
    data.pop("pricing", None)
    return data


def _strip_pricing_from_load(data: dict[str, Any]) -> dict[str, Any]:
    """Remove pricing section from load config."""
    data.pop("pricing", None)
    return data


def _strip_pricing_from_connection(data: dict[str, Any]) -> dict[str, Any]:
    """Keep connection pricing unchanged during v1.4 migration.

    Connection elements still support direct pricing. v1.4 only migrates battery
    and solar element pricing into policy rules, so connection pricing must be
    preserved.
    """
    return data


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate existing config entries to version 1.4.

    Converts internal pricing on battery/solar elements to policy subentries.
    """
    if entry.minor_version >= MINOR_VERSION:
        return True

    _LOGGER.info(
        "Migrating %s entry %s to version 1.%s",
        DOMAIN,
        entry.entry_id,
        MINOR_VERSION,
    )

    new_rules: list[dict[str, Any]] = []
    subentries_to_update: list[tuple[ConfigSubentry, dict[str, Any]]] = []
    existing_policy_subentry: ConfigSubentry | None = None

    for subentry in entry.subentries.values():
        data = dict(subentry.data)
        element_type = data.get("element_type")
        if element_type == _POLICY_TYPE and existing_policy_subentry is None:
            existing_policy_subentry = subentry
            continue

        if element_type == _BATTERY_TYPE:
            new_rules.extend(_extract_pricing_rules(subentry))
            subentries_to_update.append((subentry, _strip_pricing_from_battery(data)))

        elif element_type == _SOLAR_TYPE:
            new_rules.extend(_extract_pricing_rules(subentry))
            subentries_to_update.append((subentry, _strip_pricing_from_solar(data)))

        elif element_type == _LOAD_TYPE:
            subentries_to_update.append((subentry, _strip_pricing_from_load(data)))

        elif element_type == _CONNECTION_TYPE:
            subentries_to_update.append((subentry, _strip_pricing_from_connection(data)))

    for subentry, new_data in subentries_to_update:
        hass.config_entries.async_update_subentry(entry, subentry, data=new_data)

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
            subentry = ConfigSubentry(
                data=MappingProxyType(_policy_subentry(rules=new_rules)),
                subentry_type=_POLICY_TYPE,
                title=_POLICIES_TITLE,
                unique_id=None,
            )
            hass.config_entries.async_add_subentry(entry, subentry)
        _LOGGER.info(
            "Stored %d migrated policy rule(s) in %s subentry",
            len(new_rules),
            _POLICIES_TITLE,
        )

    hass.config_entries.async_update_entry(
        entry,
        minor_version=MINOR_VERSION,
    )

    _LOGGER.info(
        "Migration complete for %s entry %s: %d policies created",
        DOMAIN,
        entry.entry_id,
        len(new_rules),
    )
    return True

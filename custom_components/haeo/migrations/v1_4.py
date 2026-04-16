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

# Pre-sectioned battery configs (v1.2 and earlier) stored these at the top level;
# v1.3 maps them into pricing, but entries that never ran element migration may still
# have only these keys.
_LEGACY_BATTERY_DISCHARGE_COST = "discharge_cost"
_LEGACY_BATTERY_CHARGE_INCENTIVE = "early_charge_incentive"

_NONE_VALUE: dict[str, str] = {"type": "none"}


def _coalesce_pricing_field(primary: Any, fallback: Any) -> Any | None:
    """Return the first usable price value (skip missing and explicit none)."""
    for candidate in (primary, fallback):
        if candidate is None:
            continue
        if candidate == _NONE_VALUE:
            continue
        return candidate
    return None


def _policy_subentry(*, name: str, rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Build stored policy subentry data matching PolicyConfigSchema."""
    return {
        "element_type": _POLICY_TYPE,
        "name": name,
        CONF_RULES: rules,
    }


def _extract_pricing_policies(subentry: ConfigSubentry) -> list[dict[str, Any]]:
    """Extract policy subentry dicts from an element's pricing section."""
    data = dict(subentry.data)
    element_type = data.get("element_type")
    element_name = data.get("name", subentry.title)
    pricing = data.get("pricing", {})
    if not isinstance(pricing, dict):
        pricing = {}
    policies: list[dict[str, Any]] = []

    if element_type == _BATTERY_TYPE:
        discharge_price = _coalesce_pricing_field(
            pricing.get(CONF_PRICE_SOURCE_TARGET),
            data.get(_LEGACY_BATTERY_DISCHARGE_COST),
        )
        if discharge_price is not None:
            policies.append(
                _policy_subentry(
                    name=f"{element_name} Discharge Cost",
                    rules=[
                        {
                            "name": "Discharge",
                            "source": [element_name],
                            "price": discharge_price,
                        },
                    ],
                ),
            )

        charge_price = _coalesce_pricing_field(
            pricing.get(CONF_PRICE_TARGET_SOURCE),
            data.get(_LEGACY_BATTERY_CHARGE_INCENTIVE),
        )
        if charge_price is not None:
            policies.append(
                _policy_subentry(
                    name=f"{element_name} Charge Incentive",
                    rules=[
                        {
                            "name": "Charge",
                            "target": [element_name],
                            "price": charge_price,
                        },
                    ],
                ),
            )

    elif element_type == _SOLAR_TYPE:
        price_st = _coalesce_pricing_field(pricing.get(CONF_PRICE_SOURCE_TARGET), None)
        if price_st is not None:
            policies.append(
                _policy_subentry(
                    name=f"{element_name} Production Cost",
                    rules=[
                        {
                            "name": "Production",
                            "source": [element_name],
                            "price": price_st,
                        },
                    ],
                ),
            )

    return policies


def _strip_pricing_from_battery(data: dict[str, Any]) -> dict[str, Any]:
    """Remove migrated battery pricing from the pricing section and legacy top-level keys."""
    pricing = dict(data.get("pricing", {})) if isinstance(data.get("pricing"), dict) else {}
    pricing.pop(CONF_PRICE_SOURCE_TARGET, None)
    pricing.pop(CONF_PRICE_TARGET_SOURCE, None)
    data["pricing"] = pricing
    data.pop(_LEGACY_BATTERY_DISCHARGE_COST, None)
    data.pop(_LEGACY_BATTERY_CHARGE_INCENTIVE, None)
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
    """Remove pricing section from connection config."""
    data.pop("pricing", None)
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

    new_policies: list[dict[str, Any]] = []
    subentries_to_update: list[tuple[ConfigSubentry, dict[str, Any]]] = []

    for subentry in entry.subentries.values():
        data = dict(subentry.data)
        element_type = data.get("element_type")

        if element_type == _BATTERY_TYPE:
            policies = _extract_pricing_policies(subentry)
            new_policies.extend(policies)
            subentries_to_update.append((subentry, _strip_pricing_from_battery(data)))

        elif element_type == _SOLAR_TYPE:
            policies = _extract_pricing_policies(subentry)
            new_policies.extend(policies)
            subentries_to_update.append((subentry, _strip_pricing_from_solar(data)))

        elif element_type == _LOAD_TYPE:
            subentries_to_update.append((subentry, _strip_pricing_from_load(data)))

        elif element_type == _CONNECTION_TYPE:
            subentries_to_update.append((subentry, _strip_pricing_from_connection(data)))

    for subentry, new_data in subentries_to_update:
        hass.config_entries.async_update_subentry(entry, subentry, data=new_data)

    for policy_config in new_policies:
        from types import MappingProxyType  # noqa: PLC0415

        subentry = ConfigSubentry(
            data=MappingProxyType(policy_config),
            subentry_type=_POLICY_TYPE,
            title=policy_config["name"],
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(entry, subentry)
        _LOGGER.info("Created policy subentry: %s", policy_config["name"])

    hass.config_entries.async_update_entry(
        entry,
        minor_version=MINOR_VERSION,
    )

    _LOGGER.info(
        "Migration complete for %s entry %s: %d policies created",
        DOMAIN,
        entry.entry_id,
        len(new_policies),
    )
    return True

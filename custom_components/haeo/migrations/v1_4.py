"""Migration helpers for config entry version 1.4.

Migrates internal pricing from battery and solar elements to power policy subentries.

Battery:
- price_source_target (discharge wear) -> policy: Battery -> *: $X/kWh
- price_target_source (charge incentive) -> policy: * -> Battery: $X/kWh

Solar:
- price_source_target (production cost) -> policy: Solar -> *: $X/kWh
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN

_LOGGER = logging.getLogger(__name__)

MINOR_VERSION = 4

# Element types that have pricing to migrate
_BATTERY_TYPE = "battery"
_SOLAR_TYPE = "solar"
_POLICY_TYPE = "policy"  # The element type for policies in the schema


def _extract_pricing_policies(subentry: ConfigSubentry) -> list[dict[str, Any]]:
    """Extract policy configs from an element's pricing section.

    Returns a list of policy config dicts to create as new subentries.
    """
    data = dict(subentry.data)
    element_type = data.get("element_type")
    element_name = data.get("name", subentry.title)
    pricing = data.get("pricing", {})
    policies: list[dict[str, Any]] = []

    if element_type == _BATTERY_TYPE:
        # Battery discharge cost -> Battery -> *
        price_st = pricing.get("price_source_target")
        if price_st is not None and price_st != {"type": "none"}:
            policies.append(
                {
                    "element_type": _POLICY_TYPE,
                    "name": f"{element_name} Discharge Cost",
                    "endpoints": {"sources": [element_name], "destinations": ["*"]},
                    "tag_pricing": {"price_source_target": price_st},
                }
            )

        # Battery charge incentive -> * -> Battery
        price_ts = pricing.get("price_target_source")
        if price_ts is not None and price_ts != {"type": "none"}:
            policies.append(
                {
                    "element_type": _POLICY_TYPE,
                    "name": f"{element_name} Charge Incentive",
                    "endpoints": {"sources": ["*"], "destinations": [element_name]},
                    "tag_pricing": {"price_source_target": price_ts},
                }
            )

    elif element_type == _SOLAR_TYPE:
        # Solar production cost -> Solar -> *
        price_st = pricing.get("price_source_target")
        if price_st is not None and price_st != {"type": "none"}:
            policies.append(
                {
                    "element_type": _POLICY_TYPE,
                    "name": f"{element_name} Production Cost",
                    "endpoints": {"sources": [element_name], "destinations": ["*"]},
                    "tag_pricing": {"price_source_target": price_st},
                }
            )

    return policies


def _strip_pricing_from_battery(data: dict[str, Any]) -> dict[str, Any]:
    """Remove price_source_target and price_target_source from battery config."""
    pricing = dict(data.get("pricing", {}))
    pricing.pop("price_source_target", None)
    pricing.pop("price_target_source", None)
    data["pricing"] = pricing
    return data


def _strip_pricing_from_solar(data: dict[str, Any]) -> dict[str, Any]:
    """Remove pricing section from solar config."""
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

    # Collect policy configs from existing subentries
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

    # Update existing subentries (strip pricing)
    for subentry, new_data in subentries_to_update:
        hass.config_entries.async_update_subentry(entry, subentry, data=new_data)

    # Create new policy subentries
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

    # Update entry version
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

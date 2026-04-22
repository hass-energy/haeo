"""Guide validation utilities.

Functions that verify guide outcomes by inspecting HA state directly.
These run inside guide blocks but are not page interaction primitives.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.guides.ha_runner import LiveHomeAssistant

_LOGGER = logging.getLogger(__name__)


def validate_policies(hass: LiveHomeAssistant, *, expected_rules: list[str]) -> None:
    """Validate that the Policies subentry has the expected rules saved.

    Accesses the HA config entries directly via the Python API to verify
    that the policy subentry contains the expected rule names.
    """

    async def _get_policy_rules() -> list[str]:
        ha = hass.hass
        entry = next(e for e in ha.config_entries.async_entries("haeo"))
        policy_sub = next(s for s in entry.subentries.values() if s.subentry_type == "policy")
        return [r["name"] for r in policy_sub.data.get("rules", [])]

    actual_names = hass.run_coro(_get_policy_rules())
    assert actual_names == expected_rules, f"Policy rules mismatch: expected {expected_rules}, got {actual_names}"
    _LOGGER.info("Policy validation passed: %s", actual_names)


def verify_inventory_costs(hass: LiveHomeAssistant, *, battery_name: str, expected_rules: list[str]) -> None:
    """Validate that a battery subentry has the expected inventory cost rules.

    Accesses the HA config entries directly via the Python API to verify
    that the battery subentry contains the expected inventory cost rule names.
    """

    async def _get_inventory_cost_names() -> list[str]:
        ha = hass.hass
        entry = next(e for e in ha.config_entries.async_entries("haeo"))
        battery_sub = next(
            s for s in entry.subentries.values() if s.subentry_type == "battery" and s.title == battery_name
        )
        return [r["name"] for r in battery_sub.data.get("inventory_costs", [])]

    actual_names = hass.run_coro(_get_inventory_cost_names())
    assert actual_names == expected_rules, (
        f"Inventory cost rules mismatch for '{battery_name}': expected {expected_rules}, got {actual_names}"
    )
    _LOGGER.info("Inventory cost validation passed for '%s': %s", battery_name, actual_names)

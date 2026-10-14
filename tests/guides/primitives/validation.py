"""Guide validation utilities.

Functions that verify guide outcomes by inspecting HA state directly.
These run inside guide blocks but are not page interaction primitives.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.live_hass import LiveHomeAssistant

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


def validate_reserve(hass: LiveHomeAssistant, *, name: str, participants: dict[str, list[str]]) -> None:
    """Validate that a reserve was saved with the expected participants and optimized."""

    async def _get_participants() -> dict[str, list[str]]:
        ha = hass.hass
        entry = next(e for e in ha.config_entries.async_entries("haeo"))
        reserve = next(s for s in entry.subentries.values() if s.subentry_type == "reserve" and s.title == name)
        return dict(reserve.data["participants"])

    async def _get_reserve_forecast() -> list[object]:
        ha = hass.hass
        await ha.async_block_till_done()
        return next(
            state.attributes.get("forecast", [])
            for state in ha.states.async_all("sensor")
            if state.attributes.get("element_name") == name
            and state.attributes.get("output_name") == "reserve_state_of_charge"
        )

    actual = hass.run_coro(_get_participants())
    assert actual == participants, f"Reserve participants mismatch: expected {participants}, got {actual}"
    assert hass.run_coro(_get_reserve_forecast()), f"Reserve {name} has no state of charge forecast"
    _LOGGER.info("Reserve validation passed: %s", actual)

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


def validate_buffer(hass: LiveHomeAssistant, *, name: str, kind: str, participants: dict[str, list[str]]) -> None:
    """Validate that a buffer was saved with the expected kind and participants and optimized."""

    async def _get_config() -> tuple[str, dict[str, list[str]]]:
        ha = hass.hass
        entry = next(e for e in ha.config_entries.async_entries("haeo"))
        subentry = next(s for s in entry.subentries.values() if s.title == name)
        return str(subentry.data["kind"]), dict(subentry.data["participants"])

    async def _get_forecast() -> list[object]:
        ha = hass.hass
        await ha.async_block_till_done()
        return next(
            state.attributes.get("forecast", [])
            for state in ha.states.async_all("sensor")
            if state.attributes.get("element_name") == name
            and str(state.attributes.get("output_name", "")).endswith("_state_of_charge")
        )

    actual_kind, actual = hass.run_coro(_get_config())
    assert actual_kind == kind, f"{name} kind mismatch: expected {kind}, got {actual_kind}"
    assert actual == participants, f"{name} participants mismatch: expected {participants}, got {actual}"
    assert hass.run_coro(_get_forecast()), f"{name} has no state of charge forecast"
    _LOGGER.info("%s validation passed: %s", name, actual)

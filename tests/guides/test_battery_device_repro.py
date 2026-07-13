"""Live reproduction for the missing battery device/entities bug.

Drives the real Home Assistant UI config flow (via Playwright against a live
in-process instance) to create an inverter, a grid, and a battery, then
inspects the backend device and entity registries to confirm that a device
and entities are created for the battery as they are for the grid.

The battery is added last on purpose: it is the only element whose flow writes
surfaced policy rules to the policy subentry before creating its own subentry,
and that policy write triggers an eager reload that tears the entry down before
the battery subentry commits. If another element were created afterwards, its
reload would rebuild the entry and mask the bug, so the battery must be the
final commit for the reproduction to be deterministic.

Run with:
    uv run pytest tests/guides/test_battery_device_repro.py -m guide -v
"""

from __future__ import annotations

import logging
from typing import Any  # noqa: TID251  # legacy Any usage; migrate to precise types

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from playwright.sync_api import sync_playwright
import pytest

from custom_components.haeo.const import DOMAIN
from tests.guides.primitives import (
    ConstantInput,
    EntityInput,
    HAPage,
    add_battery,
    add_grid,
    add_integration,
    add_inverter,
    login,
)
from tools.guide_runner import INPUTS_FILE, load_scenario_environment
from tools.live_hass import LiveHomeAssistant, live_home_assistant

_LOGGER = logging.getLogger(__name__)


def _registry_summary(live: LiveHomeAssistant) -> dict[str, Any]:
    """Summarize, per element subentry, how many devices and entities exist."""

    async def _collect() -> dict[str, Any]:
        entries = live.hass.config_entries.async_entries(DOMAIN)
        entry = entries[0]
        device_registry = dr.async_get(live.hass)
        entity_registry = er.async_get(live.hass)

        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)

        per_subentry: dict[str, dict[str, Any]] = {}
        for subentry_id, subentry in entry.subentries.items():
            subentry_devices = [
                device
                for device in devices
                if subentry_id in device.config_entries_subentries.get(entry.entry_id, set())
            ]
            entity_count = 0
            entity_ids: list[str] = []
            for device in subentry_devices:
                device_entities = er.async_entries_for_device(
                    entity_registry, device.id, include_disabled_entities=True
                )
                entity_count += len(device_entities)
                entity_ids.extend(ent.entity_id for ent in device_entities)
            per_subentry[subentry.title] = {
                "type": str(subentry.subentry_type),
                "devices": len(subentry_devices),
                "entities": entity_count,
                "entity_ids": entity_ids,
            }
        return {
            "state": str(entry.state),
            "reason": entry.reason,
            "subentries": per_subentry,
        }

    return live.run_coro(_collect())


@pytest.mark.guide
@pytest.mark.enable_socket
@pytest.mark.timeout(300)
def test_battery_gets_device_and_entities_like_grid() -> None:
    """A battery created via the real UI flow must register a device + entities."""
    environment = load_scenario_environment()

    with live_home_assistant(timeout=120, environment=environment) as live:
        live.load_states_from_file(INPUTS_FILE)

        with (
            sync_playwright() as playwright,
            playwright.firefox.launch(headless=True) as browser,
            browser.new_context(
                viewport={"width": 1280, "height": 800},
                reduced_motion="reduce",
            ) as context,
        ):
            live.configure_context(context, dark_mode=False)
            with context.new_page() as page_obj:
                page_obj.set_default_timeout(5000)
                page = HAPage(page=page_obj, url=live.url, ha=live)

                login(page)
                add_integration(page, network_name="Sigenergy System")
                add_inverter(
                    page,
                    name="Inverter",
                    connection="Switchboard",
                    max_power_source_target=EntityInput("max active power", "Sigen Plant Max Active Power"),
                    max_power_target_source=EntityInput("max active power", "Sigen Plant Max Active Power"),
                )
                add_grid(
                    page,
                    name="Grid",
                    connection="Switchboard",
                    price_source_target=[
                        EntityInput("general price", "Home - General Price"),
                        EntityInput("general forecast", "Home - General Forecast"),
                    ],
                    price_target_source=[
                        EntityInput("feed in price", "Home - Feed In Price"),
                        EntityInput("feed in forecast", "Home - Feed In Forecast"),
                    ],
                    max_power_source_target=ConstantInput(55),
                    max_power_target_source=ConstantInput(30),
                )
                add_battery(
                    page,
                    name="Battery",
                    connection="Inverter",
                    capacity=EntityInput("rated energy", "Rated Energy Capacity"),
                    initial_charge_percentage=EntityInput("state of charge", "Battery State of Charge"),
                    max_power_target_source=EntityInput("rated charging", "Rated Charging Power"),
                    max_power_source_target=EntityInput("rated discharging", "Rated Discharging Power"),
                    min_charge_percentage=ConstantInput(10),
                    max_charge_percentage=ConstantInput(100),
                )

        live.run_coro(live.hass.async_block_till_done())
        summary = _registry_summary(live)

    _LOGGER.info("Registry summary: %s", summary)

    subentries = summary["subentries"]
    assert "Grid" in subentries, f"Grid subentry missing: {summary}"
    assert "Battery" in subentries, f"Battery subentry missing: {summary}"

    grid = subentries["Grid"]
    battery = subentries["Battery"]

    assert grid["devices"] >= 1, f"Grid should have a device: {summary}"
    assert grid["entities"] >= 1, f"Grid should have entities: {summary}"

    assert battery["devices"] >= 1, f"Battery should have a device like grid does: {summary}"
    assert battery["entities"] >= 1, f"Battery should have entities like grid does: {summary}"

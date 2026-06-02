"""Sim-specific extensions for the live Home Assistant runner.

``uv run sim`` uses persistent config directories, port-specific auth client IDs,
optional HAEO setup from scenario config, and a trusted-networks auth provider so
the browser is always logged in from loopback. Guide tests continue to use
``tools.live_hass`` directly.
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from contextlib import contextmanager
import json
from pathlib import Path
import tempfile
import threading
from types import MappingProxyType
from typing import Any
import warnings

from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.config_entries import ConfigEntries, ConfigEntryState, ConfigSubentry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import category_registry as cr
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity, translation
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers import label_registry as lr
from homeassistant.helpers import restore_state as rs
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import MIGRATION_MINOR_VERSION
from custom_components.haeo.const import CONF_RECORD_FORECASTS, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    CONF_ELEMENT_TYPE,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
)
from custom_components.haeo.flows import (
    HUB_SECTION_ADVANCED,
    HUB_SECTION_COMMON,
    HUB_SECTION_TIERS,
    get_tier_config_for_preset,
)
from tools.live_hass import (
    PROJECT_ROOT,
    LiveHomeAssistant,
    _ensure_http_started,
    _find_free_port,
    _require_component,
    auth_provider_configs,
    ensure_dev_user,
)


def _ensure_haeo_symlink(config_dir: Path) -> None:
    """Ensure custom_components/haeo symlink exists in the config directory."""
    custom_components = config_dir / "custom_components"
    custom_components.mkdir(parents=True, exist_ok=True)
    haeo_target = custom_components / "haeo"
    if not haeo_target.exists():
        haeo_target.symlink_to(PROJECT_ROOT / "custom_components" / "haeo")


async def _remove_haeo_entries(hass: HomeAssistant) -> None:
    """Remove HAEO config entries left from prior ``uv run sim`` sessions."""
    for entry in list(hass.config_entries.async_entries(DOMAIN)):
        if entry.state in (ConfigEntryState.LOADED, ConfigEntryState.SETUP_IN_PROGRESS):
            await hass.config_entries.async_unload(entry.entry_id)
        await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)


async def wait_for_sim_idle(hass: HomeAssistant) -> None:
    """Wait until scheduled setup/reload work on the HA loop has finished."""
    await hass.async_block_till_done(wait_background_tasks=True)


def _hub_entry_data_from_scenario(scenario_config: dict[str, Any]) -> dict[str, Any]:
    """Build hub config entry data from scenario config (flat or sectioned)."""
    if scenario_config.get("integration_type") == INTEGRATION_TYPE_HUB or "common" in scenario_config:
        entry_data = {
            key: value
            for key, value in scenario_config.items()
            if key
            not in (
                "participants",
                "version",
                "minor_version",
                "update_interval_minutes",
            )
        }
        if "common" in entry_data and HUB_SECTION_COMMON not in entry_data:
            entry_data[HUB_SECTION_COMMON] = entry_data.pop("common")
        if "tiers" in entry_data and HUB_SECTION_TIERS not in entry_data:
            entry_data[HUB_SECTION_TIERS] = entry_data.pop("tiers")
        if "advanced" in entry_data and HUB_SECTION_ADVANCED not in entry_data:
            entry_data[HUB_SECTION_ADVANCED] = entry_data.pop("advanced")
        entry_data.setdefault("integration_type", INTEGRATION_TYPE_HUB)
        entry_data.setdefault(HUB_SECTION_ADVANCED, {})
        return entry_data

    tiers_data = scenario_config.get("tiers") or scenario_config
    horizon_preset = scenario_config.get(CONF_HORIZON_PRESET) or scenario_config.get("horizon_preset")
    if not isinstance(horizon_preset, str) or not horizon_preset:
        msg = "Scenario hub config must include horizon_preset (for example 3_days)"
        raise ValueError(msg)

    common_section = {
        CONF_NAME: scenario_config.get(CONF_NAME, "Test Hub"),
        CONF_HORIZON_PRESET: horizon_preset,
    }
    if horizon_preset != "custom":
        tiers_section = get_tier_config_for_preset(horizon_preset)
    else:
        tiers_section = {
            CONF_TIER_1_COUNT: tiers_data["tier_1_count"],
            CONF_TIER_1_DURATION: tiers_data["tier_1_duration"],
            CONF_TIER_2_COUNT: tiers_data.get("tier_2_count", 0),
            CONF_TIER_2_DURATION: tiers_data.get("tier_2_duration", 5),
            CONF_TIER_3_COUNT: tiers_data.get("tier_3_count", 0),
            CONF_TIER_3_DURATION: tiers_data.get("tier_3_duration", 30),
            CONF_TIER_4_COUNT: tiers_data.get("tier_4_count", 0),
            CONF_TIER_4_DURATION: tiers_data.get("tier_4_duration", 60),
        }

    return {
        "integration_type": INTEGRATION_TYPE_HUB,
        HUB_SECTION_COMMON: common_section,
        HUB_SECTION_TIERS: tiers_section,
        HUB_SECTION_ADVANCED: scenario_config.get(HUB_SECTION_ADVANCED, {}),
        CONF_RECORD_FORECASTS: scenario_config.get(CONF_RECORD_FORECASTS, False),
    }


async def setup_haeo_entry(hass: HomeAssistant, scenario_config: dict[str, Any]) -> MockConfigEntry:
    """Create and set up a HAEO hub config entry from scenario config data."""
    await _remove_haeo_entries(hass)

    mock_config_entry = MockConfigEntry(
        domain=DOMAIN,
        data=_hub_entry_data_from_scenario(scenario_config),
        version=scenario_config.get("version", 1),
        minor_version=scenario_config.get("minor_version", MIGRATION_MINOR_VERSION),
    )
    mock_config_entry.add_to_hass(hass)

    for name, config in scenario_config["participants"].items():
        subentry = ConfigSubentry(
            data=MappingProxyType(config),
            subentry_type=config[CONF_ELEMENT_TYPE],
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(mock_config_entry, subentry)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return mock_config_entry


async def _setup_sim_home_assistant_async(
    port: int,
    config_dir: str,
    *,
    timezone: str,
) -> HomeAssistant:
    """Bootstrap Home Assistant for sim with loopback auto-login dev auth."""
    storage_dir = Path(config_dir) / ".storage"
    storage_dir.mkdir(parents=True, exist_ok=True)
    onboarding_storage = storage_dir / "onboarding"
    onboarding_data = {
        "version": 4,
        "minor_version": 1,
        "key": "onboarding",
        "data": {"done": ["user", "core_config", "analytics", "integration"]},
    }
    onboarding_storage.write_text(json.dumps(onboarding_data))

    hass = HomeAssistant(config_dir)

    hass.config.location_name = "Test Home"
    hass.config.latitude = 32.87336
    hass.config.longitude = -117.22743
    hass.config.elevation = 0
    await hass.config.async_set_time_zone(timezone)
    hass.config.skip_pip = True
    hass.config.skip_pip_packages = []

    loader.async_setup(hass)

    hass.config_entries = ConfigEntries(hass, {"_": "placeholder"})

    entity.async_setup(hass)
    translation.async_setup(hass)

    await ar.async_load(hass)
    await cr.async_load(hass)
    await dr.async_load(hass)
    await er.async_load(hass)
    await fr.async_load(hass)
    await ir.async_load(hass)
    await lr.async_load(hass)
    await rs.async_load(hass)
    await hass.config_entries.async_initialize()

    # Drop entries persisted from earlier sim runs so we do not boot into a
    # pile of parallel HAEO setups that race the browser auto-login redirect.
    await _remove_haeo_entries(hass)

    hass.auth = await auth_manager_from_config(
        hass,
        provider_configs=auth_provider_configs(),
        module_configs=[],
    )

    warnings.filterwarnings("ignore", category=DeprecationWarning, module="aiohttp")
    try:
        from aiohttp.web_exceptions import NotAppKeyWarning  # noqa: PLC0415

        warnings.filterwarnings("ignore", category=NotAppKeyWarning)
    except ImportError:
        pass

    await _require_component(hass, "http", {"http": {"server_port": port}})
    await _require_component(hass, "websocket_api", {})
    await _require_component(hass, "auth", {})
    await _require_component(hass, "onboarding", {})

    from homeassistant.components.onboarding import async_is_onboarded  # noqa: PLC0415

    if not async_is_onboarded(hass):
        msg = "Onboarding bypass failed - check storage file format and timing"
        raise RuntimeError(msg)

    await ensure_dev_user(hass)

    await _require_component(hass, "frontend", {})
    await _require_component(hass, "config", {})

    from homeassistant.helpers.recorder import async_initialize_recorder  # noqa: PLC0415

    async_initialize_recorder(hass)
    await _require_component(hass, "recorder", {"recorder": {"commit_interval": 1}})

    await _require_component(hass, "calendar", {})
    await _require_component(hass, "local_calendar", {})

    hass.set_state(CoreState.running)
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    await _ensure_http_started(hass)

    return hass


def _run_sim_hass_thread(
    port: int,
    config_dir: str,
    timezone: str,
    hass_holder: list[HomeAssistant],
    loop_holder: list[asyncio.AbstractEventLoop],
    ready_event: threading.Event,
    async_stop_event_holder: list[asyncio.Event],
    error_holder: list[Exception],
) -> None:
    """Run sim Home Assistant in a thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop_holder.append(loop)

    async def _run() -> None:
        async_stop_event = asyncio.Event()
        async_stop_event_holder.append(async_stop_event)

        try:
            hass = await _setup_sim_home_assistant_async(
                port,
                config_dir,
                timezone=timezone,
            )
            hass_holder.append(hass)
            ready_event.set()

            await async_stop_event.wait()
            await hass.async_stop(force=True)

        except Exception as e:
            error_holder.append(e)
            ready_event.set()

    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


def _start_sim_home_assistant(
    config_dir: Path,
    *,
    timeout: float,
    port: int | None,
    timezone: str,
) -> tuple[LiveHomeAssistant, threading.Thread]:
    """Start sim HA in a background thread and return the live instance."""
    _ensure_haeo_symlink(config_dir)
    resolved_port = port if port is not None else _find_free_port()
    hass_holder: list[HomeAssistant] = []
    loop_holder: list[asyncio.AbstractEventLoop] = []
    error_holder: list[Exception] = []
    async_stop_event_holder: list[asyncio.Event] = []
    ready_event = threading.Event()

    thread = threading.Thread(
        target=_run_sim_hass_thread,
        args=(
            resolved_port,
            str(config_dir),
            timezone,
            hass_holder,
            loop_holder,
            ready_event,
            async_stop_event_holder,
            error_holder,
        ),
        daemon=True,
    )
    thread.start()

    if not ready_event.wait(timeout=timeout):
        if loop_holder and async_stop_event_holder:
            loop_holder[0].call_soon_threadsafe(async_stop_event_holder[0].set)
        thread.join(timeout=5)
        msg = f"Home Assistant did not start within {timeout}s"
        raise TimeoutError(msg)

    if error_holder:
        if loop_holder and async_stop_event_holder:
            loop_holder[0].call_soon_threadsafe(async_stop_event_holder[0].set)
        thread.join(timeout=5)
        raise error_holder[0]

    hass = hass_holder[0]
    loop = loop_holder[0]
    async_stop_event = async_stop_event_holder[0]

    instance = LiveHomeAssistant(
        hass=hass,
        url=f"http://127.0.0.1:{resolved_port}",
        port=resolved_port,
        loop=loop,
        _stop_event=async_stop_event,
    )
    return instance, thread


@contextmanager
def live_sim_home_assistant(
    timeout: float = 60.0,
    *,
    config_dir: Path | None = None,
    port: int | None = None,
    environment: dict[str, Any] | None = None,
) -> Generator[LiveHomeAssistant]:
    """Context manager for a sim Home Assistant instance with optional persistent config."""
    scenario_environment = environment or {}
    timezone = str(scenario_environment.get("timezone", "UTC"))

    if config_dir is None:
        with tempfile.TemporaryDirectory(prefix="ha_live_") as tmp_dir:
            instance, thread = _start_sim_home_assistant(
                Path(tmp_dir),
                timeout=timeout,
                port=port,
                timezone=timezone,
            )
            try:
                yield instance
            finally:
                instance.stop()
                thread.join(timeout=10)
    else:
        config_dir.mkdir(parents=True, exist_ok=True)
        instance, thread = _start_sim_home_assistant(
            config_dir,
            timeout=timeout,
            port=port,
            timezone=timezone,
        )
        try:
            yield instance
        finally:
            instance.stop()
            thread.join(timeout=10)

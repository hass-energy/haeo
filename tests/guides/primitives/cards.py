"""Render HAEO's Lovelace cards in guides from the live instance's data.

Guides show what HAEO plans, not only how to configure it. These primitives
load the card bundles the integration serves into a page of their own, feed
them the live Home Assistant state the card would see in a dashboard, and
capture the result into the current step's screenshots.

Each capture re-runs the optimizer first, so the card reflects every change
the guide has made so far.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import date, datetime
import json
import logging
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.const import DOMAIN, STATIC_CARD_STATIC_PATH

from .capture import ScreenshotContext, guide_step

if TYPE_CHECKING:
    from playwright.sync_api import Page

    from tools.live_hass import LiveHomeAssistant

    from .ha_page import HAPage

_LOGGER = logging.getLogger(__name__)

_PREVIEW_PATH = "/__haeo_card_preview__"
_RENDER_TIMEOUT_MS = 15000

# Home Assistant's default theme colors, so cards render as they would on a dashboard
_THEME_VARIABLES = {
    False: {
        "--card-background-color": "#ffffff",
        "--primary-text-color": "#212121",
        "--secondary-text-color": "#727272",
        "--divider-color": "rgba(0, 0, 0, 0.12)",
        "--primary-color": "#009ac7",
        "background": "#f5f5f5",
    },
    True: {
        "--card-background-color": "#1c1c1c",
        "--primary-text-color": "#e1e1e1",
        "--secondary-text-color": "#9b9b9b",
        "--divider-color": "rgba(225, 225, 225, 0.12)",
        "--primary-color": "#009ac7",
        "background": "#111111",
    },
}


def _json_default(value: object) -> str:
    """Serialize datetimes in state attributes the way the frontend receives them."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _hub_entry_id(hass: LiveHomeAssistant) -> str:
    return hass.hass.config_entries.async_entries(DOMAIN)[0].entry_id


def optimize(hass: LiveHomeAssistant) -> None:
    """Run the optimizer now and wait for every entity to pick up the result."""

    async def _optimize() -> None:
        await hass.hass.async_block_till_done()
        await hass.hass.services.async_call(DOMAIN, "optimize", {"config_entry": _hub_entry_id(hass)}, blocking=True)
        await hass.hass.async_block_till_done()

    hass.run_coro(_optimize(), timeout=120)


def set_input(hass: LiveHomeAssistant, *, element: str, field: str, value: float) -> None:
    """Set one of an element's input entities, as you would from a dashboard."""

    async def _find_entity() -> str:
        return next(
            state.entity_id
            for state in hass.hass.states.async_all("number")
            if state.attributes.get("element_name") == element and state.attributes.get("field_name") == field
        )

    entity_id = hass.run_coro(_find_entity())
    hass.call_service("number", "set_value", {"entity_id": entity_id, "value": value})
    _LOGGER.info("Set %s to %s", entity_id, value)


def _hass_payload(hass: LiveHomeAssistant, entity_filter: Callable[[str, dict[str, object]], bool]) -> str:
    """Return the ``hass`` object a card reads, as JSON, limited to the entities that pass the filter."""

    async def _collect() -> dict[str, object]:
        ha = hass.hass
        entities = er.async_get(ha)
        devices = dr.async_get(ha)
        states = {
            state.entity_id: {
                "entity_id": state.entity_id,
                "state": state.state,
                "attributes": dict(state.attributes),
            }
            for state in ha.states.async_all()
            if entity_filter(state.entity_id, dict(state.attributes))
        }
        registry_entries = {entity_id: entities.async_get(entity_id) for entity_id in states}
        return {
            "language": "en",
            "states": states,
            "entities": {
                entity_id: {"platform": entry.platform, "device_id": entry.device_id}
                for entity_id, entry in registry_entries.items()
                if entry is not None
            },
            "devices": {
                device.id: {"config_entries": list(device.config_entries)} for device in devices.devices.values()
            },
        }

    return json.dumps(hass.run_coro(_collect()), default=_json_default)


def _is_dark(page: HAPage) -> bool:
    """Return whether the guide is capturing the dark theme."""
    selected = page.page.evaluate("() => localStorage.getItem('selectedTheme')")
    return isinstance(selected, str) and bool(json.loads(selected).get("dark"))


def _render_card(
    page: HAPage, hass: LiveHomeAssistant, *, tag: str, config: Mapping[str, object], hass_json: str, step: str
) -> None:
    """Render a card on a page of its own and capture it into the current step."""
    ctx = ScreenshotContext.current()
    if ctx is None:
        return

    dark = _is_dark(page)
    theme = _THEME_VARIABLES[dark]
    variables = "".join(f"{name}: {value};" for name, value in theme.items() if name.startswith("--"))
    color_scheme = "dark" if dark else "light"
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; height: 100%; background: {theme["background"]}; }}
  body {{ {variables} box-sizing: border-box; padding: 24px; display: flex; color-scheme: {color_scheme}; }}
  .card {{ flex: 1; background: var(--card-background-color); border-radius: 12px; padding: 16px;
           box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15); display: flex; }}
  {tag} {{ flex: 1; }}
</style>
<script type="module" src="{STATIC_CARD_STATIC_PATH}/{tag}.min.js"></script>
</head>
<body><div class="card"></div></body>
</html>"""

    # A context of its own shows times in Home Assistant's time zone, as a dashboard would
    browser = page.page.context.browser
    assert browser is not None
    viewport = page.page.viewport_size
    context = browser.new_context(
        viewport=viewport,
        timezone_id=hass.hass.config.time_zone,
        color_scheme="dark" if dark else "light",
        reduced_motion="reduce",
    )
    preview: Page = context.new_page()
    try:
        preview.route(f"{page.url}{_PREVIEW_PATH}", lambda route: route.fulfill(content_type="text/html", body=html))
        preview.goto(f"{page.url}{_PREVIEW_PATH}")
        preview.wait_for_function(f"() => customElements.get('{tag}') !== undefined", timeout=_RENDER_TIMEOUT_MS)
        preview.evaluate(
            """([tag, config, hassJson]) => {
                const card = document.createElement(tag);
                card.setConfig(config);
                card.hass = JSON.parse(hassJson);
                document.querySelector('.card').appendChild(card);
            }""",
            [tag, config, hass_json],
        )
        preview.wait_for_function(
            f"() => document.querySelector('{tag}')?.shadowRoot?.querySelector('svg path') != null",
            timeout=_RENDER_TIMEOUT_MS,
        )
        ctx.capture(preview, step)
    finally:
        context.close()


@guide_step
def show_forecast_card(
    page: HAPage,
    hass: LiveHomeAssistant,
    *,
    step: str,
    elements: list[str],
    horizon: str = "full",
    inputs: list[str] | None = None,
) -> None:
    """Capture the forecast card showing the planned forecasts of the named elements.

    Args:
        page: The guide's page.
        hass: The live Home Assistant instance.
        step: Name of the captured screenshot, shown as its slideshow label.
        elements: Elements whose forecasts the card shows.
        horizon: How much of the forecast the card shows, as one of its horizon presets.
        inputs: Elements whose input forecasts and limits the card also shows, alongside the plan.

    """
    optimize(hass)
    hass_json = _hass_payload(
        hass,
        lambda _entity_id, attributes: (
            attributes.get("element_name") in elements
            and "forecast" in attributes
            and ("config_mode" not in attributes or attributes.get("element_name") in (inputs or []))
        ),
    )
    config = {
        "type": "custom:haeo-forecast-card",
        "hub_entry_id": _hub_entry_id(hass),
        "default_horizon": horizon,
        "tooltip_visible": False,
    }
    _render_card(page, hass, tag="haeo-forecast-card", config=config, hass_json=hass_json, step=step)
    _LOGGER.info("Captured forecast card for %s", ", ".join(elements))


@guide_step
def show_topology_card(page: HAPage, hass: LiveHomeAssistant, *, step: str) -> None:
    """Capture the topology card for the whole network."""
    optimize(hass)
    hass_json = _hass_payload(hass, lambda _entity_id, attributes: "topology" in attributes)
    config = {"type": "custom:haeo-topology-card", "hub_entry_id": _hub_entry_id(hass)}
    _render_card(page, hass, tag="haeo-topology-card", config=config, hass_json=hass_json, step=step)
    _LOGGER.info("Captured topology card")


__all__ = ["optimize", "set_input", "show_forecast_card", "show_topology_card"]

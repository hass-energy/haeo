"""Render HAEO's Lovelace cards in guides from the live instance's data.

Guides show what HAEO plans, not only how to configure it. These primitives
load the card bundles the integration serves into a page of their own, feed
them the live Home Assistant state the card would see in a dashboard, and
save the rendered card as an SVG figure. The figure carries the card's own
markup and styles, so it stays sharp at any size, legend included.

Each capture re-runs the optimizer first, so the card reflects every change
the guide has made so far.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import date, datetime
import json
import logging
from typing import TYPE_CHECKING
from xml.sax.saxutils import quoteattr

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
_HOST_CLASS = "haeo-card-host"
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


def _card_css(dark: bool) -> str:
    """Return the styles of the card's frame, shared by the preview page and the saved figure."""
    theme = _THEME_VARIABLES[dark]
    variables = "".join(f"{name}: {value};" for name, value in theme.items() if name.startswith("--"))
    color_scheme = "dark" if dark else "light"
    return (
        f".card {{ {variables} color-scheme: {color_scheme}; flex: 1; box-sizing: border-box; display: flex;"
        " background: var(--card-background-color); border-radius: 12px; padding: 16px;"
        ' font-family: Roboto, "Noto Sans", system-ui, sans-serif; color: var(--primary-text-color); }'
        f" .card > * {{ flex: 1; }}"
    )


# Flattens the card's shadow root into plain markup, with its styles scoped to a
# wrapper standing in for the host element, so the card renders inside an SVG.
_SERIALIZE_CARD_JS = """
(hostClass) => {
  const card = document.querySelector('.card');
  const host = card.firstElementChild;
  const flat = document.createElement('div');
  flat.className = hostClass;
  let css = '';
  for (const node of host.shadowRoot.childNodes) {
    if (node.nodeName === 'STYLE') css += node.textContent;
    else flat.appendChild(node.cloneNode(true));
  }
  const style = document.createElement('style');
  style.textContent = css.replaceAll(':host', '.' + hostClass);
  flat.prepend(style);
  const frame = card.cloneNode(false);
  frame.appendChild(flat);
  const rect = card.getBoundingClientRect();
  return { markup: new XMLSerializer().serializeToString(frame), width: rect.width, height: rect.height };
}
"""


@contextmanager
def _card_page(
    page: HAPage,
    hass: LiveHomeAssistant,
    *,
    tag: str,
    config: Mapping[str, object],
    hass_json: str,
    fill_height: bool,
) -> Iterator[Page]:
    """Open a page of its own showing the card, ready to capture, and close it afterwards.

    A card that fills the page's height takes the viewport's shape, as a chart
    does on a dashboard. Otherwise the card takes the height of its content.
    """
    dark = _is_dark(page)
    layout = "height: 100%; display: flex;" if fill_height else "display: block;"
    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin: 0; background: {_THEME_VARIABLES[dark]["background"]}; }}
  html {{ height: 100%; }}
  body {{ box-sizing: border-box; padding: 24px; {layout} }}
  .card {{ box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15); }}
  {_card_css(dark)}
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
        yield preview
    finally:
        context.close()


def _card_svg(preview: Page, *, dark: bool) -> str:
    """Return the card on the preview page as a standalone SVG."""
    card = preview.evaluate(_SERIALIZE_CARD_JS, _HOST_CLASS)
    width = round(card["width"])
    height = round(card["height"])
    frame_style = f"width: {width}px; height: {height}px; display: flex;"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
        f"<style>{_card_css(dark)}</style>"
        f'<foreignObject x="0" y="0" width="{width}" height="{height}">'
        f'<div xmlns="http://www.w3.org/1999/xhtml" style={quoteattr(frame_style)}>'
        f"{card['markup']}</div></foreignObject></svg>\n"
    )


def _render_card(
    page: HAPage,
    hass: LiveHomeAssistant,
    *,
    tag: str,
    config: Mapping[str, object],
    hass_json: str,
    step: str,
    fill_height: bool,
) -> None:
    """Render a card and save it as a figure of the current step, when captures are being taken."""
    ctx = ScreenshotContext.current()
    if ctx is not None:
        with _card_page(page, hass, tag=tag, config=config, hass_json=hass_json, fill_height=fill_height) as preview:
            ctx.save_figure(step, _card_svg(preview, dark=_is_dark(page)))


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
        step: Name of the figure, shown as its label.
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
    _render_card(page, hass, tag="haeo-forecast-card", config=config, hass_json=hass_json, step=step, fill_height=True)
    _LOGGER.info("Captured forecast card for %s", ", ".join(elements))


@guide_step
def show_topology_card(page: HAPage, hass: LiveHomeAssistant, *, step: str) -> None:
    """Capture the topology card for the whole network."""
    optimize(hass)
    hass_json = _hass_payload(hass, lambda _entity_id, attributes: "topology" in attributes)
    config = {"type": "custom:haeo-topology-card", "hub_entry_id": _hub_entry_id(hass)}
    _render_card(page, hass, tag="haeo-topology-card", config=config, hass_json=hass_json, step=step, fill_height=False)
    _LOGGER.info("Captured topology card")


__all__ = ["optimize", "set_input", "show_forecast_card", "show_topology_card"]

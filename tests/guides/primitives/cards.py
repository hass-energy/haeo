"""Render HAEO's Lovelace cards in guides from the live instance's data.

Guides show what HAEO plans, not only how to configure it. These primitives
load the card bundles the integration serves into a page of their own, feed
them the live Home Assistant state the card would see in a dashboard, and
save the rendered card as an SVG figure. The figure carries the card's own
markup and styles, so it stays sharp at any size, legend included.

Each capture re-runs the optimizer first, so the card reflects every change
the guide has made so far. While captures are paused, such as when a guide
replays another as its setup, the cards are not rendered at all.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
import json
import logging
from typing import TYPE_CHECKING
from xml.sax.saxutils import quoteattr

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.json import json_dumps

from custom_components.haeo import CARD_STATIC_DIR, card_static_url
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.elements.policy import CONF_ENABLED, CONF_RULE_NAME, CONF_RULES

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
        "--error-color": "#db4437",
        "background": "#f5f5f5",
    },
    True: {
        "--card-background-color": "#1c1c1c",
        "--primary-text-color": "#e1e1e1",
        "--secondary-text-color": "#9b9b9b",
        "--divider-color": "rgba(225, 225, 225, 0.12)",
        "--primary-color": "#009ac7",
        "--error-color": "#db4437",
        "background": "#111111",
    },
}


def _hub_entry_id(hass: LiveHomeAssistant) -> str:
    return hass.hass.config_entries.async_entries(DOMAIN)[0].entry_id


def optimize(hass: LiveHomeAssistant) -> None:
    """Run the optimizer now and wait for every entity to pick up the result."""

    async def _optimize() -> None:
        await hass.hass.async_block_till_done()
        await hass.hass.services.async_call(DOMAIN, "optimize", {"config_entry": _hub_entry_id(hass)}, blocking=True)
        await hass.hass.async_block_till_done()

    hass.run_coro(_optimize(), timeout=120)


def _find_input(hass: LiveHomeAssistant, domain: str, *, element: str, field: str) -> str:
    """Return the entity of an element's input, named by its field or by its path such as ``pricing.price``.

    Raises:
        ValueError: If no input or more than one matches, such as a field name
            used in several sections of the element.

    """

    async def _matches() -> list[str]:
        return [
            state.entity_id
            for state in hass.hass.states.async_all(domain)
            if state.attributes.get("element_name") == element
            and field in (state.attributes.get("field_name"), state.attributes.get("field_path"))
        ]

    matches = hass.run_coro(_matches())
    if len(matches) != 1:
        msg = f"Expected one {domain} input {field!r} on {element}, found {matches or 'none'}"
        raise ValueError(msg)
    return matches[0]


def set_input(hass: LiveHomeAssistant, *, element: str, field: str, value: float) -> None:
    """Set one of an element's input entities, as you would from a dashboard.

    Name the field by its path, such as ``pricing.price``, when the element uses its name in more than one section.
    """
    entity_id = _find_input(hass, "number", element=element, field=field)
    hass.call_service("number", "set_value", {"entity_id": entity_id, "value": value})
    _LOGGER.info("Set %s to %s", entity_id, value)


def set_policy_rule(hass: LiveHomeAssistant, *, rule: str, enabled: bool) -> None:
    """Turn a policy rule on or off with its enabled switch, as you would from a dashboard."""

    async def _rule_path() -> tuple[str, str]:
        entry = hass.hass.config_entries.async_entries(DOMAIN)[0]
        policies = next(
            subentry for subentry in entry.subentries.values() if subentry.subentry_type == ElementType.POLICY
        )
        index = next(i for i, item in enumerate(policies.data[CONF_RULES]) if item[CONF_RULE_NAME] == rule)
        return policies.title, f"{CONF_RULES}.{index}.{CONF_ENABLED}"

    element, path = hass.run_coro(_rule_path())
    entity_id = _find_input(hass, "switch", element=element, field=path)
    hass.call_service("switch", "turn_on" if enabled else "turn_off", {"entity_id": entity_id})
    _LOGGER.info("Turned %s %s", entity_id, "on" if enabled else "off")


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

    return json_dumps(hass.run_coro(_collect()))


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
# ``:host(selector)`` becomes the wrapper with that selector.
# Waits until the card's markup stops changing across several painted frames,
# so lazily loaded parts, resize-driven layout, and the legend are all in place.
_WAIT_SETTLED_JS = """
async () => {
  const root = document.querySelector('.card').firstElementChild.shadowRoot;
  const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  if (document.fonts) await document.fonts.ready;
  let previous = null;
  let stable = 0;
  for (let attempt = 0; attempt < 100; attempt++) {
    await frame();
    await new Promise((resolve) => setTimeout(resolve, 50));
    const markup = root.innerHTML;
    stable = markup === previous ? stable + 1 : 0;
    if (stable >= 3) return true;
    previous = markup;
  }
  return false;
}
"""

# Turns elements off with their legend toggles, as a reader clicking the legend would
_HIDE_ELEMENTS_JS = """
(names) => {
  const root = document.querySelector('.card').firstElementChild.shadowRoot;
  for (const name of names) {
    const toggle = root.querySelector(`[title="Toggle ${name} series"]`);
    if (toggle === null) throw new Error(`No legend toggle for ${name}`);
    toggle.click();
  }
}
"""

_SERIALIZE_CARD_JS = r"""
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
  if (css.includes(':host-context')) throw new Error('Cards using :host-context cannot be flattened');
  const style = document.createElement('style');
  style.textContent = css.replace(/:host\(([^)]*)\)/g, '.' + hostClass + '$1').replaceAll(':host', '.' + hostClass);
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
    dark: bool,
    hidden: Sequence[str] = (),
) -> Iterator[Page]:
    """Open a page of its own showing the card, ready to capture, and close it afterwards.

    A card that fills the page's height takes the viewport's shape, as a chart
    does on a dashboard. Otherwise the card takes the height of its content.
    """
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
<script type="module" src="{card_static_url(CARD_STATIC_DIR)}/{tag}.min.js"></script>
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
        if hidden:
            preview.evaluate(_HIDE_ELEMENTS_JS, list(hidden))
        if not preview.evaluate(_WAIT_SETTLED_JS):
            msg = f"{tag} kept changing and never settled for a capture"
            raise RuntimeError(msg)
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
    ctx: ScreenshotContext,
    *,
    tag: str,
    config: Mapping[str, object],
    entity_filter: Callable[[str, dict[str, object]], bool],
    step: str,
    fill_height: bool,
    hidden: Sequence[str] = (),
) -> None:
    """Optimize, render a card from the entities that pass the filter, and save it as a figure of the current step."""
    optimize(hass)
    hass_json = _hass_payload(hass, entity_filter)
    dark = _is_dark(page)
    with _card_page(
        page, hass, tag=tag, config=config, hass_json=hass_json, fill_height=fill_height, dark=dark, hidden=hidden
    ) as preview:
        ctx.save_figure(step, _card_svg(preview, dark=dark))


@guide_step
def show_forecast_card(
    page: HAPage,
    hass: LiveHomeAssistant,
    *,
    step: str,
    elements: list[str],
    horizon: str = "full",
    inputs: list[str] | None = None,
    hidden: list[str] | None = None,
) -> None:
    """Capture the forecast card showing the planned forecasts of the named elements.

    Args:
        page: The guide's page.
        hass: The live Home Assistant instance.
        step: Name of the figure, shown as its label.
        elements: Elements whose planned forecasts the card shows.
        horizon: How much of the forecast the card shows, as one of its horizon presets.
        inputs: Elements whose input forecasts and limits the card also shows, alongside the plan.
        hidden: Elements the card lists in its legend but draws nothing for, as if turned off
            there. Listing the same elements in a set of figures keeps their legends, and so
            their charts, the same size.

    """
    ctx = ScreenshotContext.current()
    if ctx is None:
        return
    shown_inputs = inputs or []

    def _shows(_entity_id: str, attributes: dict[str, object]) -> bool:
        if "forecast" not in attributes:
            return False
        if "config_mode" in attributes:
            return attributes.get("element_name") in shown_inputs
        return attributes.get("element_name") in elements

    config = {
        "type": "custom:haeo-forecast-card",
        "hub_entry_id": _hub_entry_id(hass),
        "default_horizon": horizon,
        "tooltip_visible": False,
    }
    _render_card(
        page,
        hass,
        ctx,
        tag="haeo-forecast-card",
        config=config,
        entity_filter=_shows,
        step=step,
        fill_height=True,
        hidden=hidden or [],
    )
    _LOGGER.info("Captured forecast card for %s", ", ".join(elements))


@guide_step
def show_topology_card(page: HAPage, hass: LiveHomeAssistant, *, step: str) -> None:
    """Capture the topology card for the whole network."""
    ctx = ScreenshotContext.current()
    if ctx is None:
        return
    config = {"type": "custom:haeo-topology-card", "hub_entry_id": _hub_entry_id(hass)}
    _render_card(
        page,
        hass,
        ctx,
        tag="haeo-topology-card",
        config=config,
        entity_filter=lambda _entity_id, attributes: "topology" in attributes,
        step=step,
        fill_height=False,
    )
    _LOGGER.info("Captured topology card")


__all__ = ["optimize", "set_input", "set_policy_rule", "show_forecast_card", "show_topology_card"]

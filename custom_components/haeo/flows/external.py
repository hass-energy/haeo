"""External step utilities for React-based configuration UI.

This module provides utilities for redirecting config flows to the React webapp
using Home Assistant's external step pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import DOMAIN

if TYPE_CHECKING:
    from custom_components.haeo import HaeoConfigEntry

# Base URL path for the React frontend (registered in __init__.py)
# Note: Must match FRONTEND_URL_PATH in __init__.py
FRONTEND_URL_PATH = "haeo_static"


def build_external_url(
    hass: HomeAssistant,
    *,
    flow_id: str,
    entry_id: str | None = None,
    subentry_type: str | None = None,
    subentry_id: str | None = None,
    mode: str = "create",
) -> str:
    """Build the URL for the React configuration webapp.

    Args:
        hass: Home Assistant instance.
        flow_id: The active config flow ID.
        entry_id: Parent config entry ID (for element flows).
        subentry_type: Type of element being configured.
        subentry_id: ID of existing subentry (for reconfigure flows).
        mode: Either "create" or "reconfigure".

    Returns:
        Full URL to the React webapp with query parameters.

    """
    # Get the base URL from Home Assistant configuration
    # We use relative URLs since the React app is served from the same origin
    base_url = f"/{FRONTEND_URL_PATH}/"

    # Build query parameters
    params: list[str] = [f"flow_id={flow_id}"]

    if entry_id:
        params.append(f"entry_id={entry_id}")

    if subentry_type:
        params.append(f"subentry_type={subentry_type}")

    if subentry_id:
        params.append(f"subentry_id={subentry_id}")

    params.append(f"mode={mode}")

    return f"{base_url}?{'&'.join(params)}"


def get_hub_external_url(
    hass: HomeAssistant,
    flow_id: str,
) -> str:
    """Build external URL for hub configuration flow.

    Args:
        hass: Home Assistant instance.
        flow_id: The active config flow ID.

    Returns:
        URL for the React hub configuration page.

    """
    return build_external_url(hass, flow_id=flow_id)


def get_element_external_url(
    hass: HomeAssistant,
    flow_id: str,
    entry_id: str,
    subentry_type: str,
    subentry_id: str | None = None,
) -> str:
    """Build external URL for element configuration flow.

    Args:
        hass: Home Assistant instance.
        flow_id: The active config flow ID.
        entry_id: Parent hub config entry ID.
        subentry_type: Type of element (battery, grid, solar, etc.).
        subentry_id: Existing subentry ID if reconfiguring.

    Returns:
        URL for the React element configuration page.

    """
    mode = "reconfigure" if subentry_id else "create"
    return build_external_url(
        hass,
        flow_id=flow_id,
        entry_id=entry_id,
        subentry_type=subentry_type,
        subentry_id=subentry_id,
        mode=mode,
    )


def get_options_external_url(
    hass: HomeAssistant,
    flow_id: str,
    entry_id: str,
) -> str:
    """Build external URL for options flow.

    Args:
        hass: Home Assistant instance.
        flow_id: The active options flow ID.
        entry_id: Config entry ID being configured.

    Returns:
        URL for the React options configuration page.

    """
    return build_external_url(
        hass,
        flow_id=flow_id,
        entry_id=entry_id,
        mode="options",
    )


__all__ = [
    "FRONTEND_URL_PATH",
    "build_external_url",
    "get_element_external_url",
    "get_hub_external_url",
    "get_options_external_url",
]

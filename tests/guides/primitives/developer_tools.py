"""Developer Tools primitives for guide automation.

High-level functions for interacting with the Home Assistant Developer Tools UI.
These are separate from the config-flow primitives in haeo.py since they interact
with a different part of the system, but they reuse HAPage form interaction methods.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .capture import guide_step

if TYPE_CHECKING:
    from .ha_page import HAPage

_LOGGER = logging.getLogger(__name__)


@guide_step
def save_diagnostics(page: HAPage, *, time: str) -> None:
    """Call haeo.save_diagnostics with a historic timestamp via Developer Tools.

    Navigates to Developer Tools > Actions, selects the save_diagnostics service,
    selects the config entry, fills in the target time, and performs the action.

    Args:
        page: The HAPage instance for browser interaction.
        time: The target datetime as "YYYY-MM-DD HH:MM" string.

    """
    _LOGGER.info("Saving historic diagnostics at %s...", time)

    page.navigate_to_developer_tools_actions()
    page.fill_service_action("haeo.save_diagnostics", "Save diagnostics")
    page.select_config_entry("Sigenergy System")
    page.fill_datetime_field("Time", time)
    page.click_perform_action()

    _LOGGER.info("Historic diagnostics saved")

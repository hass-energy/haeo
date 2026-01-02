"""Battery section element configuration flow using external step pattern.

This flow redirects to the React webapp for configuration instead of
using Home Assistant's native form UI.
"""

from typing import Any, ClassVar

from custom_components.haeo.flows.external_flow import ExternalSubentryFlowHandler

from .schema import ELEMENT_TYPE, BatterySectionConfigSchema


class BatterySectionExternalFlowHandler(ExternalSubentryFlowHandler):
    """Handle battery section element configuration via React webapp."""

    ELEMENT_TYPE: ClassVar[str] = ELEMENT_TYPE
    CONFIG_SCHEMA: ClassVar[type] = BatterySectionConfigSchema
    INPUT_FIELDS: ClassVar[tuple[Any, ...]] = ()  # Battery section doesn't use INPUT_FIELDS


__all__ = ["BatterySectionExternalFlowHandler"]

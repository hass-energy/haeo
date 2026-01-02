"""Node element configuration flow using external step pattern.

This flow redirects to the React webapp for configuration instead of
using Home Assistant's native form UI.
"""

from typing import Any, ClassVar

from custom_components.haeo.flows.external_flow import ExternalSubentryFlowHandler

from .schema import ELEMENT_TYPE, INPUT_FIELDS, NodeConfigSchema


class NodeExternalFlowHandler(ExternalSubentryFlowHandler):
    """Handle node element configuration via React webapp."""

    ELEMENT_TYPE: ClassVar[str] = ELEMENT_TYPE
    CONFIG_SCHEMA: ClassVar[type] = NodeConfigSchema
    INPUT_FIELDS: ClassVar[tuple[Any, ...]] = INPUT_FIELDS


__all__ = ["NodeExternalFlowHandler"]

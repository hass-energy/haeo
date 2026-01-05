"""Fixtures for config flow tests."""

import pytest
from homeassistant.core import HomeAssistant

from custom_components.haeo.flows.sentinels import async_setup_sentinel_entities


@pytest.fixture(autouse=True)
async def setup_sentinel_entities(hass: HomeAssistant) -> None:
    """Set up the configurable sentinel entity for flow tests."""
    await async_setup_sentinel_entities(hass)

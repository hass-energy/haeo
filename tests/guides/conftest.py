"""Configuration for guide tests.

Guide tests run Home Assistant in-process with browser automation.
They do NOT use pytest-homeassistant-custom-component fixtures
since they need a full HTTP server for Playwright.

Run via pytest with:
    uv run pytest tests/guides/ -m guide
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register guide marker."""
    config.addinivalue_line(
        "markers",
        "guide: mark test as a guide test (runs full HA with HTTP, needs network)",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> bool:
    """Override the global fixture that depends on pytest-homeassistant-custom-component.

    Guide tests run their own HA instance and don't use the hass fixture,
    so the global auto_enable_custom_integrations fixture (which depends on
    enable_custom_integrations → hass) would fail. This local override
    prevents that fixture from being requested.
    """
    return True

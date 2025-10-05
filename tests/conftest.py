"""Test configuration and fixtures."""

import pytest

# Enable custom component for testing
pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations) -> bool:
    """Enable loading custom integrations in all tests."""
    return enable_custom_integrations is None

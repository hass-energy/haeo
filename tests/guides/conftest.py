"""Configuration for guide tests.

Guide tests are designed to run Home Assistant in-process with browser
automation. They do NOT use pytest-homeassistant-custom-component fixtures
since they need a full HTTP server for Playwright.

These tests should be run with:
    uv run python tests/guides/<test_file>.py

Or via pytest with explicit socket enabling:
    uv run pytest tests/guides/ --force-enable-socket -m guide
"""


def pytest_configure(config):
    """Register guide marker."""
    config.addinivalue_line(
        "markers",
        "guide: mark test as a guide test (runs full HA with HTTP, needs network)",
    )

"""Configuration for guide tests.

Guide tests run Home Assistant in-process with browser automation.
They do NOT use pytest-homeassistant-custom-component fixtures
since they need a full HTTP server for Playwright.

Run via pytest with:
    uv run pytest tests/guides/ -m guide
"""

from __future__ import annotations

from collections.abc import Generator
import datetime

from homeassistant.util import dt as dt_util
import pytest
from pytest_socket import enable_socket

# Guide tests run a full HA instance in a background thread. The global
# filterwarnings = ["error"] from pyproject.toml turns third-party
# DeprecationWarnings (aiohttp, HA internals) into RuntimeErrors that
# crash the background event loop. Reset to "default" for guide tests
# since we don't control third-party warning behavior.
#
# HA's frontend static handler can emit unraisable ResourceWarnings when
# the browser disconnects during shutdown on CI. Ignore pytest's wrapper so
# guide screenshot assertions remain the signal.
#
# Note: pytestmark in a conftest does not propagate to collected tests under
# pytest >= 9.0, so socket enablement is done via an autouse fixture below
# rather than a usefixtures mark here.
pytestmark = [
    pytest.mark.filterwarnings("default"),
    pytest.mark.filterwarnings("ignore::ResourceWarning"),
    pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning"),
]


@pytest.fixture(autouse=True)
def _enable_socket_for_guides() -> None:  # pyright: ignore[reportUnusedFunction]
    """Re-enable real sockets for guide tests.

    pytest-homeassistant-custom-component disables sockets globally; guide
    tests need real sockets to find a free port and run a live HA HTTP
    server for Playwright. The `socket_enabled` fixture from pytest-socket
    used to be applied via a module-level `pytestmark` here, but pytest 9
    no longer propagates conftest-level pytestmark to test items.
    """
    enable_socket()


def pytest_configure(config: pytest.Config) -> None:
    """Register guide marker."""
    config.addinivalue_line(
        "markers",
        "guide: mark test as a guide test (runs full HA with HTTP, needs network)",
    )


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations() -> bool:  # pyright: ignore[reportUnusedFunction]
    """Override the global fixture that depends on pytest-homeassistant-custom-component.

    Guide tests run their own HA instance and don't use the hass fixture,
    so the global auto_enable_custom_integrations fixture (which depends on
    enable_custom_integrations → hass) would fail. This local override
    prevents that fixture from being requested.
    """
    return True


@pytest.fixture(autouse=True)
def _restore_timezone() -> Generator[None]:  # pyright: ignore[reportUnusedFunction]
    """Restore dt_util.DEFAULT_TIME_ZONE after test.

    The live HA instance sets the timezone to ZoneInfo('UTC') via
    async_set_time_zone(), but pytest-homeassistant-custom-component
    expects datetime.timezone.utc at teardown.
    """
    yield
    # Reset to datetime.UTC which is what the pytest plugin expects
    dt_util.set_default_time_zone(datetime.UTC)

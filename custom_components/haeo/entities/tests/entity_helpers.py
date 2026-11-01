"""Helpers shared by the entity tests."""

from collections.abc import Callable
from unittest.mock import Mock

from homeassistant.helpers.entity import Entity


def mock_state_writes(entity: Entity, side_effect: Callable[[], None] | None = None) -> Mock:
    """Replace the entity's state writes with a mock, and return the mock.

    ``async_write_ha_state`` is final, so the mock is set on the instance's attributes.
    """
    write = Mock(side_effect=side_effect)
    vars(entity)["async_write_ha_state"] = write
    return write

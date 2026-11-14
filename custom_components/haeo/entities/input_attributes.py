"""State attributes every input entity shows about the store behind it."""

from datetime import UTC, datetime

from custom_components.haeo.core.data.input_store import InputStore

# The source an input holds the last reading of for longest, and when that source lost its reading
ATTR_HELD_SOURCE_ENTITY = "held_source_entity"
ATTR_HELD_SINCE = "held_since"


def held_reading_attributes(store: InputStore) -> dict[str, object]:
    """Return the attributes naming the oldest reading an input holds, or none while every source has a reading."""
    if (oldest := store.oldest_held_source) is None:
        return {}
    entity_id, since = oldest
    return {ATTR_HELD_SOURCE_ENTITY: entity_id, ATTR_HELD_SINCE: datetime.fromtimestamp(since, tz=UTC)}


__all__ = ["ATTR_HELD_SINCE", "ATTR_HELD_SOURCE_ENTITY", "held_reading_attributes"]

"""Tests for the config entry version 1.6 migration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_PUBLIC_CHARGING_PRICE,
    DEFAULT_PUBLIC_CHARGING_PRICE,
    SECTION_PUBLIC_CHARGING,
)
from custom_components.haeo.migrations import v1_6


@pytest.mark.parametrize(
    ("public_charging", "expected"),
    [
        pytest.param(None, as_constant_value(DEFAULT_PUBLIC_CHARGING_PRICE), id="no_section"),
        pytest.param({}, as_constant_value(DEFAULT_PUBLIC_CHARGING_PRICE), id="no_price"),
        pytest.param(
            {CONF_PUBLIC_CHARGING_PRICE: as_none_value()},
            as_constant_value(DEFAULT_PUBLIC_CHARGING_PRICE),
            id="none_price",
        ),
        pytest.param(
            {CONF_PUBLIC_CHARGING_PRICE: as_constant_value(0.7)}, as_constant_value(0.7), id="constant_price_kept"
        ),
        pytest.param(
            {CONF_PUBLIC_CHARGING_PRICE: as_entity_value(["sensor.public_price"])},
            as_entity_value(["sensor.public_price"]),
            id="entity_price_kept",
        ),
    ],
)
async def test_an_ev_without_a_public_charging_price_gets_the_default(
    hass: HomeAssistant, public_charging: dict[str, object] | None, expected: object
) -> None:
    """An EV saved with no public charging price gets the default as a constant, and a set price is kept."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=5)
    entry.add_to_hass(hass)
    data: dict[str, object] = {CONF_ELEMENT_TYPE: ElementType.EV, CONF_NAME: "Atto 2"}
    if public_charging is not None:
        data[SECTION_PUBLIC_CHARGING] = public_charging
    ev = ConfigSubentry(data=MappingProxyType(data), subentry_type=ElementType.EV, title="Atto 2", unique_id=None)
    hass.config_entries.async_add_subentry(entry, ev)

    assert await v1_6.async_migrate_entry(hass, entry)

    migrated = entry.subentries[ev.subentry_id].data
    assert migrated[SECTION_PUBLIC_CHARGING] == {CONF_PUBLIC_CHARGING_PRICE: expected}
    assert migrated[CONF_NAME] == "Atto 2"
    assert entry.minor_version == v1_6.MINOR_VERSION

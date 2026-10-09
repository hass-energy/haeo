"""Tests for the v1.5 junction-only node migration."""

from collections.abc import Mapping
from types import MappingProxyType
from unittest.mock import patch

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import migrations
from custom_components.haeo.const import DOMAIN
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target
from custom_components.haeo.core.schema.elements import load, node
from custom_components.haeo.core.schema.migrations.v1_5 import migrate_element_config
from custom_components.haeo.migrations import v1_5


def _add_subentry(hass: HomeAssistant, entry: MockConfigEntry, data: Mapping[str, object]) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=str(data[CONF_ELEMENT_TYPE]),
        title=str(data[CONF_NAME]),
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        pytest.param(
            {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard", "role": {"is_source": True}},
            {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard"},
            id="node_role_removed",
        ),
        pytest.param(
            {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard"},
            {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard"},
            id="node_without_role_unchanged",
        ),
        pytest.param(
            {CONF_ELEMENT_TYPE: load.ELEMENT_TYPE, CONF_NAME: "Load", "role": {"is_source": True}},
            {CONF_ELEMENT_TYPE: load.ELEMENT_TYPE, CONF_NAME: "Load", "role": {"is_source": True}},
            id="other_element_unchanged",
        ),
    ],
)
def test_migrate_element_config(data: dict[str, object], expected: dict[str, object]) -> None:
    """Only node elements lose their role section."""
    assert migrate_element_config(data) == expected


@pytest.mark.parametrize(
    ("role", "warns"),
    [
        pytest.param({"is_source": True, "is_sink": False}, True, id="raw_source"),
        pytest.param(
            {"is_source": {"type": "constant", "value": True}, "is_sink": {"type": "constant", "value": False}},
            True,
            id="constant_wrapped_source",
        ),
        pytest.param({"is_source": False, "is_sink": True}, True, id="raw_sink"),
        pytest.param({"is_source": False, "is_sink": False}, False, id="junction"),
        pytest.param(
            {"is_source": {"type": "constant", "value": False}, "is_sink": {"type": "constant", "value": False}},
            False,
            id="constant_wrapped_junction",
        ),
    ],
)
async def test_async_migrate_entry_strips_node_role(
    hass: HomeAssistant,
    role: dict[str, object],
    *,
    warns: bool,
) -> None:
    """v1.5 migration turns every node into a junction and removes its role switches."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={}, version=1, minor_version=4)
    entry.add_to_hass(hass)
    switchboard = _add_subentry(
        hass,
        entry,
        {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard", "role": role},
    )
    load_data = {
        CONF_ELEMENT_TYPE: load.ELEMENT_TYPE,
        CONF_NAME: "Load",
        "connection": as_connection_target("Switchboard"),
    }
    load_subentry = _add_subentry(hass, entry, load_data)

    registry = er.async_get(hass)
    role_switches = [
        registry.async_get_or_create(
            "switch",
            DOMAIN,
            f"{entry.entry_id}_{switchboard.subentry_id}_{field}",
            config_entry=entry,
        )
        for field in ("is_source", "is_sink")
    ]
    other_switch = registry.async_get_or_create(
        "switch",
        DOMAIN,
        f"{entry.entry_id}_{load_subentry.subentry_id}_curtailment",
        config_entry=entry,
    )

    with patch.object(v1_5._LOGGER, "warning") as warning:
        assert await v1_5.async_migrate_entry(hass, entry) is True

    assert entry.minor_version == v1_5.MINOR_VERSION
    assert dict(entry.subentries[switchboard.subentry_id].data) == {
        CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
        CONF_NAME: "Switchboard",
    }
    assert dict(entry.subentries[load_subentry.subentry_id].data) == load_data
    for switch in role_switches:
        assert registry.async_get(switch.entity_id) is None
    assert registry.async_get(other_switch.entity_id) is not None
    assert warning.called is warns


async def test_async_migrate_entry_skips_current_entries(hass: HomeAssistant) -> None:
    """Entries already at v1.5 are left alone."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={}, version=1, minor_version=v1_5.MINOR_VERSION)
    entry.add_to_hass(hass)
    switchboard = _add_subentry(
        hass,
        entry,
        {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard", "role": {"is_source": True}},
    )

    assert await v1_5.async_migrate_entry(hass, entry) is True

    assert entry.subentries[switchboard.subentry_id].data["role"] == {"is_source": True}


async def test_full_migration_repairs_legacy_source_node(hass: HomeAssistant) -> None:
    """A pre-v1.3 flat node configured as a source migrates all the way to a junction."""
    entry = MockConfigEntry(domain=DOMAIN, title="Hub", data={CONF_NAME: "Hub"}, version=1, minor_version=0)
    entry.add_to_hass(hass)
    switchboard = _add_subentry(
        hass,
        entry,
        {CONF_ELEMENT_TYPE: node.ELEMENT_TYPE, CONF_NAME: "Switchboard", "is_source": True, "is_sink": False},
    )

    assert await migrations.async_migrate_entry(hass, entry) is True

    assert entry.minor_version == migrations.MIGRATION_MINOR_VERSION
    assert dict(entry.subentries[switchboard.subentry_id].data) == {
        CONF_ELEMENT_TYPE: node.ELEMENT_TYPE,
        CONF_NAME: "Switchboard",
    }

"""Tests for grid element config flow."""

import json
from pathlib import Path
from types import MappingProxyType
from typing import (
    Any,  # noqa: TID251  # element flows are created from the registry, which a static flow type cannot express
)
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
import custom_components.haeo
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    SchemaValue,
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
)
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.grid import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.conftest import create_flow, section_selectors, section_suggested_values

CONF_IMPORT_PRICE = CONF_PRICE_SOURCE_TARGET
CONF_EXPORT_PRICE = CONF_PRICE_TARGET_SOURCE
CONF_IMPORT_LIMIT = CONF_MAX_POWER_SOURCE_TARGET
CONF_EXPORT_LIMIT = CONF_MAX_POWER_TARGET_SOURCE


def _grid_input(
    import_price: SchemaValue,
    export_price: SchemaValue,
    *,
    name: str = "Test Grid",
    limits: dict[str, SchemaValue] | None = None,
) -> dict[str, object]:
    """Build the grid form's submitted values."""
    return {
        CONF_NAME: name,
        CONF_CONNECTION: "TestNode",
        SECTION_PRICING: {CONF_IMPORT_PRICE: import_price, CONF_EXPORT_PRICE: export_price},
        SECTION_POWER_LIMITS: limits or {},
    }


def _add_grid(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    import_price: SchemaValue,
    export_price: SchemaValue,
    *,
    limits: dict[str, SchemaValue] | None = None,
) -> ConfigSubentry:
    """Add a stored grid connected to TestNode."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                **_grid_input(import_price, export_price, limits=limits),
                CONF_CONNECTION: as_connection_target("TestNode"),
            }
        ),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry) -> Any:
    """Create a flow reconfiguring the given grid."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})
    return flow


@pytest.mark.parametrize(
    "price",
    [
        pytest.param(as_constant_value(0.25), id="constant"),
        pytest.param(as_entity_value(["sensor.import_price"]), id="entity"),
    ],
)
async def test_user_step_stores_submitted_prices(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    price: SchemaValue,
) -> None:
    """A new grid stores its prices as submitted, and a missing price is reported on the pricing section."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Grid", "data": {}})

    invalid_result = await flow.async_step_user(user_input=_grid_input(as_none_value(), as_constant_value(0.05)))
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_PRICING: "required"}

    result = await flow.async_step_user(user_input=_grid_input(price, as_constant_value(0.05)))

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = flow.async_create_entry.call_args.kwargs["data"]
    assert data[SECTION_PRICING] == {CONF_IMPORT_PRICE: price, CONF_EXPORT_PRICE: as_constant_value(0.05)}


async def test_untouched_new_grid_form_explains_why_it_is_reshown(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting the new grid form as it opens re-shows it with a visible, translated error on the prices."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            SECTION_PRICING: section_suggested_values(form, SECTION_PRICING),
            SECTION_POWER_LIMITS: section_suggested_values(form, SECTION_POWER_LIMITS),
        },
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_PRICING: "required"}
    translations = json.loads((Path(custom_components.haeo.__file__).parent / "translations" / "en.json").read_text())
    assert "required" in translations["config_subentries"][ELEMENT_TYPE]["error"]


async def test_required_prices_do_not_offer_none(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Grid prices are required, so their selectors do not offer leaving them unset while power limits do."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )

    assert all("none" not in selector.config["kinds"] for selector in section_selectors(form, SECTION_PRICING).values())
    assert all(
        "none" in selector.config["kinds"] for selector in section_selectors(form, SECTION_POWER_LIMITS).values()
    )


async def test_submitted_values_are_validated_into_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """The form's input selectors turn what the frontend submits into the values the grid stores."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set("sensor.export_price", "0.05", {"unit_of_measurement": "$/kWh"})

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            SECTION_PRICING: {
                CONF_IMPORT_PRICE: {"type": "constant", "value": "0.3"},
                CONF_EXPORT_PRICE: {"type": "entity", "value": "sensor.export_price"},
            },
            SECTION_POWER_LIMITS: {
                CONF_IMPORT_LIMIT: {"type": "entity", "value": []},
                CONF_EXPORT_LIMIT: {"type": "constant", "value": 5},
            },
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None
    assert data[SECTION_PRICING] == {
        CONF_IMPORT_PRICE: as_constant_value(0.3),
        CONF_EXPORT_PRICE: as_entity_value(["sensor.export_price"]),
    }
    assert data[SECTION_POWER_LIMITS] == {
        CONF_IMPORT_LIMIT: as_none_value(),
        CONF_EXPORT_LIMIT: as_constant_value(5.0),
    }


async def test_submitted_entities_the_field_does_not_offer_are_rejected(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """An entity the price field does not offer, such as one in another unit, fails validation."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    hass.states.async_set("sensor.outdoor_temperature", "21", {"unit_of_measurement": "°C"})

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )
    with pytest.raises(InvalidData):
        await hass.config_entries.subentries.async_configure(
            form["flow_id"],
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                SECTION_PRICING: {
                    CONF_IMPORT_PRICE: {"type": "entity", "value": ["sensor.outdoor_temperature"]},
                    CONF_EXPORT_PRICE: {"type": "constant", "value": 0.05},
                },
                SECTION_POWER_LIMITS: {},
            },
        )


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfiguring a grid from entity prices to constants stores the constants."""
    subentry = _add_grid(hass, hub_entry, as_entity_value(["sensor.import"]), as_entity_value(["sensor.export"]))
    flow = _reconfigure_flow(hass, hub_entry, subentry)

    invalid_result = await flow.async_step_reconfigure(user_input=_grid_input(as_none_value(), as_constant_value(0.05)))
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_PRICING: "required"}

    result = await flow.async_step_reconfigure(user_input=_grid_input(as_constant_value(0.3), as_constant_value(0.08)))

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"
    data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert data[SECTION_PRICING] == {
        CONF_IMPORT_PRICE: as_constant_value(0.3),
        CONF_EXPORT_PRICE: as_constant_value(0.08),
    }


# Each kind of value an optional field can hold
_LIMIT_VALUES: dict[str, SchemaValue] = {
    "entity": as_entity_value(["sensor.import_limit"]),
    "constant": as_constant_value(7.5),
    "none": as_none_value(),
}


@pytest.mark.parametrize("kind", list(_LIMIT_VALUES))
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    kind: str,
) -> None:
    """Reopening a grid shows each stored value, whichever kind it is."""
    subentry = _add_grid(
        hass,
        hub_entry,
        as_entity_value(["sensor.import1", "sensor.import2"]),
        as_constant_value(0.05),
        limits={CONF_IMPORT_LIMIT: _LIMIT_VALUES[kind]},
    )

    form = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(user_input=None)

    assert section_suggested_values(form, SECTION_PRICING) == {
        CONF_IMPORT_PRICE: as_entity_value(["sensor.import1", "sensor.import2"]),
        CONF_EXPORT_PRICE: as_constant_value(0.05),
    }
    assert section_suggested_values(form, SECTION_POWER_LIMITS)[CONF_IMPORT_LIMIT] == _LIMIT_VALUES[kind]


@pytest.mark.parametrize(
    ("stored_kind", "submitted_kind"),
    [(stored, submitted) for stored in _LIMIT_VALUES for submitted in _LIMIT_VALUES if stored != submitted],
)
async def test_reshown_form_keeps_the_submitted_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    stored_kind: str,
    submitted_kind: str,
) -> None:
    """A form re-shown with an error shows each submitted value rather than the stored one."""
    subentry = _add_grid(
        hass,
        hub_entry,
        as_constant_value(0.3),
        as_constant_value(0.05),
        limits={CONF_IMPORT_LIMIT: _LIMIT_VALUES[stored_kind]},
    )

    form = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(
        user_input=_grid_input(
            as_constant_value(0.3),
            as_constant_value(0.05),
            name="TestNode",
            limits={CONF_IMPORT_LIMIT: _LIMIT_VALUES[submitted_kind]},
        )
    )

    assert form.get("errors") == {CONF_NAME: "name_exists"}
    assert section_suggested_values(form, SECTION_POWER_LIMITS)[CONF_IMPORT_LIMIT] == _LIMIT_VALUES[submitted_kind]

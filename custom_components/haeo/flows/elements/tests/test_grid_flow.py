"""Tests for grid element config flow."""

from collections.abc import Mapping
import json
from pathlib import Path
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER, ConfigSubentry, SubentryFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
import custom_components.haeo
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
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
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.field_schema import (
    CHOICE_CONSTANT,
    CHOICE_ENTITY,
    CHOICE_NONE,
    NormalizingChooseSelector,
)

CONF_IMPORT_PRICE = CONF_PRICE_SOURCE_TARGET
CONF_EXPORT_PRICE = CONF_PRICE_TARGET_SOURCE
CONF_IMPORT_LIMIT = CONF_MAX_POWER_SOURCE_TARGET
CONF_EXPORT_LIMIT = CONF_MAX_POWER_TARGET_SOURCE
SECTION_LIMITS = SECTION_POWER_LIMITS


def _wrap_input(flat: Mapping[str, object]) -> dict[str, object]:
    """Wrap flat grid input values into sectioned config."""
    if SECTION_PRICING in flat:
        return dict(flat)
    pricing = {
        CONF_PRICE_SOURCE_TARGET: flat[CONF_PRICE_SOURCE_TARGET],
        CONF_PRICE_TARGET_SOURCE: flat[CONF_PRICE_TARGET_SOURCE],
    }
    power_limits = {
        key: flat[key] for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE) if key in flat
    }
    return {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
        SECTION_PRICING: pricing,
        SECTION_POWER_LIMITS: power_limits,
    }


def _wrap_config(flat: Mapping[str, object]) -> dict[str, object]:
    """Wrap flat grid config values into sectioned config with element type."""
    if SECTION_PRICING in flat:
        return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat}
    config = _wrap_input(flat)
    connection = config.get(CONF_CONNECTION)
    if isinstance(connection, str):
        config[CONF_CONNECTION] = as_connection_target(connection)
    return {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **config}


# --- Tests for validation errors ---


# --- Tests for single-step flow with choose selector ---


async def test_user_step_with_constant_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with constant values using choose selector format
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: 0.25,
            CONF_EXPORT_PRICE: 0.05,
            CONF_IMPORT_LIMIT: 10.0,
            CONF_EXPORT_LIMIT: 10.0,
        }
    )
    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    invalid_result = await flow.async_step_user(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_PRICING: "required"}

    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant schema values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_constant_value(0.25)
    assert create_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_constant_value(0.05)


async def test_user_step_with_entity_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Grid",
            "data": {},
        }
    )

    # Submit with entity selections
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: ["sensor.import_price"],
            CONF_EXPORT_PRICE: ["sensor.export_price"],
            CONF_IMPORT_LIMIT: 10.0,
            CONF_EXPORT_LIMIT: 10.0,
        }
    )
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the entity schema values (single entity)
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_entity_value(["sensor.import_price"])
    assert create_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_entity_value(["sensor.export_price"])


def _section_selectors(form: SubentryFlowResult, section_key: str) -> dict[str, NormalizingChooseSelector]:
    """Return the choose selectors inside a section of a shown form, keyed by field name."""
    data_schema = form.get("data_schema")
    assert data_schema is not None
    section_schema = data_schema.schema[section_key].schema
    return {str(marker): selector for marker, selector in section_schema.schema.items()}


def _preselected_choice_input(selector: NormalizingChooseSelector) -> dict[str, object]:
    """Build what the frontend submits for a choose selector left on its preselected choice."""
    choice = next(iter(selector.config["choices"]))
    empty_values: dict[str, object] = {CHOICE_ENTITY: [], CHOICE_NONE: ""}
    return {"active_choice": choice, choice: empty_values.get(choice)}


async def test_untouched_new_grid_form_explains_why_it_is_reshown(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting the new grid form with prices left untouched re-shows it with a visible, translated error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )
    pricing = {
        field: _preselected_choice_input(selector)
        for field, selector in _section_selectors(form, SECTION_PRICING).items()
    }

    result = await hass.config_entries.subentries.async_configure(
        form["flow_id"],
        {CONF_NAME: "Test Grid", CONF_CONNECTION: "TestNode", SECTION_PRICING: pricing, SECTION_POWER_LIMITS: {}},
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {SECTION_PRICING: "required"}
    translations = json.loads((Path(custom_components.haeo.__file__).parent / "translations" / "en.json").read_text())
    assert "required" in translations["config_subentries"][ELEMENT_TYPE]["error"]


async def test_required_prices_do_not_offer_none(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Grid prices are required, so their selectors offer no "none" choice while power limits do."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    form = await hass.config_entries.subentries.async_init(
        (hub_entry.entry_id, ELEMENT_TYPE),
        context={"source": SOURCE_USER},
    )
    pricing = _section_selectors(form, SECTION_PRICING).values()
    limits = _section_selectors(form, SECTION_POWER_LIMITS).values()

    assert all(CHOICE_NONE not in selector.config["choices"] for selector in pricing)
    assert all(CHOICE_NONE in selector.config["choices"] for selector in limits)


async def test_frontend_constant_submission_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Constant prices submitted in the frontend's choose selector shape create the grid."""
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
            SECTION_PRICING: {
                CONF_IMPORT_PRICE: {"active_choice": CHOICE_CONSTANT, CHOICE_CONSTANT: 0.3},
                CONF_EXPORT_PRICE: {"active_choice": CHOICE_CONSTANT, CHOICE_CONSTANT: 0.1},
            },
            SECTION_POWER_LIMITS: {
                CONF_IMPORT_LIMIT: {"active_choice": CHOICE_NONE, CHOICE_CONSTANT: 100},
                CONF_EXPORT_LIMIT: {"active_choice": CHOICE_CONSTANT, CHOICE_CONSTANT: 5},
            },
        },
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    data = result.get("data")
    assert data is not None
    assert data[SECTION_PRICING] == {
        CONF_IMPORT_PRICE: as_constant_value(0.3),
        CONF_EXPORT_PRICE: as_constant_value(0.1),
    }
    assert data[SECTION_POWER_LIMITS] == {
        CONF_IMPORT_LIMIT: as_none_value(),
        CONF_EXPORT_LIMIT: as_constant_value(5.0),
    }


# --- Tests for reconfigure flow ---


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with constant values should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with entity links
    existing_config = _wrap_config(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: as_entity_value(["sensor.import"]),
            CONF_EXPORT_PRICE: as_entity_value(["sensor.export"]),
        }
    )
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Validate required field handling
    invalid_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: [],
            CONF_EXPORT_PRICE: 0.05,
        }
    )
    invalid_result = await flow.async_step_reconfigure(user_input=invalid_input)
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_PRICING: "required"}

    # Change to constant values
    user_input = _wrap_input(
        {
            CONF_NAME: "Test Grid",
            CONF_CONNECTION: "TestNode",
            CONF_IMPORT_PRICE: 0.30,
            CONF_EXPORT_PRICE: 0.08,
        }
    )
    result = await flow.async_step_reconfigure(user_input=user_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][SECTION_PRICING][CONF_IMPORT_PRICE] == as_constant_value(0.30)
    assert update_kwargs["data"][SECTION_PRICING][CONF_EXPORT_PRICE] == as_constant_value(0.08)


@pytest.mark.parametrize(
    ("config_values", "expected_defaults"),
    [
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_constant_value(0.30),
                CONF_EXPORT_PRICE: as_constant_value(0.08),
            },
            {
                CONF_IMPORT_PRICE: 0.30,
                CONF_EXPORT_PRICE: 0.08,
            },
            id="constant_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_entity_value(["sensor.import_price"]),
                CONF_EXPORT_PRICE: as_entity_value(["sensor.export_price"]),
            },
            {
                CONF_IMPORT_PRICE: ["sensor.import_price"],
                CONF_EXPORT_PRICE: ["sensor.export_price"],
            },
            id="entity_values",
        ),
        pytest.param(
            {
                CONF_NAME: "Test Grid",
                CONF_CONNECTION: "TestNode",
                CONF_IMPORT_PRICE: as_entity_value(["sensor.import1", "sensor.import2"]),
                CONF_EXPORT_PRICE: as_entity_value(["sensor.export"]),
            },
            {
                CONF_IMPORT_PRICE: ["sensor.import1", "sensor.import2"],
                CONF_EXPORT_PRICE: ["sensor.export"],
            },
            id="entity_list",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    config_values: dict[str, object],
    expected_defaults: dict[str, object],
) -> None:
    """Reconfigure defaults reflect schema values."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    existing_config = _wrap_config(config_values)
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_reconfigure(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(ELEMENT_TYPE)
    defaults = flow._build_defaults("Test Grid", input_fields, dict(existing_subentry.data))
    assert defaults[SECTION_PRICING][CONF_IMPORT_PRICE] == expected_defaults[CONF_IMPORT_PRICE]
    assert defaults[SECTION_PRICING][CONF_EXPORT_PRICE] == expected_defaults[CONF_EXPORT_PRICE]


# --- Tests for _is_valid_choose_value ---

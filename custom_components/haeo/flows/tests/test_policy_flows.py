"""Tests for the policy element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
import voluptuous as vol

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE as NODE_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.policy import (
    CONF_ENABLED,
    CONF_PRICE,
    CONF_RULE_NAME,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    PolicyRuleConfig,
)
from custom_components.haeo.core.schema.elements.policy import ELEMENT_TYPE as POLICY_ELEMENT_TYPE
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.none_value import as_none_value
from custom_components.haeo.flows.elements.policy import (
    ACTION_DELETE,
    ACTION_EDIT,
    CHOICE_NODES,
    CONF_ACTION,
    CONF_RULE,
    POLICIES_TITLE,
    PolicySubentryFlowHandler,
)
from custom_components.haeo.flows.field_schema import CHOICE_NONE


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub config entry with some participant subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB},
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)

    for name in ("Solar", "Grid", "Battery", "Load"):
        subentry = ConfigSubentry(
            data=MappingProxyType({CONF_ELEMENT_TYPE: NODE_ELEMENT_TYPE, CONF_NAME: name}),
            subentry_type=NODE_ELEMENT_TYPE,
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(entry, subentry)

    return entry


def _create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> PolicySubentryFlowHandler:
    """Create a policy flow handler wired to the test hub."""
    flow = PolicySubentryFlowHandler()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, POLICY_ELEMENT_TYPE)
    return flow


def _make_policy_subentry(rules: list[PolicyRuleConfig]) -> ConfigSubentry:
    """Create a policy subentry with the provided rules."""
    data = MappingProxyType(
        {
            CONF_ELEMENT_TYPE: POLICY_ELEMENT_TYPE,
            CONF_NAME: POLICIES_TITLE,
            CONF_RULES: rules,
        }
    )
    return ConfigSubentry(
        data=data,
        subentry_type=POLICY_ELEMENT_TYPE,
        title=POLICIES_TITLE,
        unique_id=None,
    )


def _get_suggested_value(result: Any, field_name: str) -> Any:
    """Extract the suggested_value for a field from a flow result's data_schema."""
    data_schema = result.get("data_schema")
    assert data_schema is not None
    for key in data_schema.schema:
        if getattr(key, "schema", None) == field_name:
            desc = getattr(key, "description", None)
            if desc is not None:
                return desc.get("suggested_value")
    return None


# --- User step (adding a policy rule) ---


async def test_user_step_shows_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """First call to async_step_user shows the rule form."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_user_step_creates_entry_when_none_exists(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a rule when no policy subentry exists creates one."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "Solar Export",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
            CONF_PRICE: 0.02,
        }
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_ELEMENT_TYPE] == POLICY_ELEMENT_TYPE
    assert len(created_data[CONF_RULES]) == 1
    assert created_data[CONF_RULES][0]["name"] == "Solar Export"
    assert created_data[CONF_RULES][0]["source"] == ["Solar"]
    assert created_data[CONF_RULES][0]["price"] == as_constant_value(0.02)


async def test_user_step_appends_to_existing_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a rule when a policy subentry exists appends to it."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.async_update_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"},
    )

    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "Grid Charge",
            CONF_SOURCE: ["Grid"],
            CONF_TARGET: ["Battery"],
            CONF_PRICE: 0.05,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert len(update_data[CONF_RULES]) == 2
    assert update_data[CONF_RULES][0]["name"] == "Solar Export"
    assert update_data[CONF_RULES][1]["name"] == "Grid Charge"


async def test_user_step_any_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Source/target defaulting to 'any' omits them from stored config."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "Global Policy",
            CONF_SOURCE: "",
            CONF_TARGET: "",
            CONF_PRICE: 0.05,
        }
    )

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    rule = created_data[CONF_RULES][0]
    assert "source" not in rule
    assert "target" not in rule


async def test_user_step_rejects_missing_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a rule without a name shows an error."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULE_NAME: "missing_name"}


async def test_user_step_rejects_same_source_target(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting source == target (non-wildcard) shows an error."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "Self Loop",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Solar"],
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"base": "source_target_same"}


# --- Reconfigure step (manage existing rules) ---


async def test_reconfigure_shows_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure loads existing rules and shows the selection form."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"


async def test_reconfigure_aborts_when_empty(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with no rules aborts."""
    subentry = _make_policy_subentry([])
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "no_rules"


async def test_reconfigure_edit_shows_edit_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting edit navigates to the edit_rule step."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)

    result = await flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_EDIT,
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_rule"


async def test_reconfigure_delete_updates_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting delete removes the rule and saves."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
        {
            "name": "Grid Charge",
            "source": ["Grid"],
            "target": ["Battery"],
            "price": as_constant_value(0.05),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"},
    )

    await flow.async_step_reconfigure(user_input=None)

    result = await flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_DELETE,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert len(update_data[CONF_RULES]) == 1
    assert update_data[CONF_RULES][0]["name"] == "Grid Charge"


# --- Edit rule step ---


async def test_edit_rule_updates_and_saves(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule updates it and saves the subentry."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"},
    )

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_EDIT,
        }
    )

    result = await flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Solar Export Updated",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
            CONF_PRICE: 0.03,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert update_data[CONF_RULES][0]["name"] == "Solar Export Updated"
    assert update_data[CONF_RULES][0]["price"] == as_constant_value(0.03)


async def test_edit_rule_rejects_duplicate_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule to a name that already exists shows an error."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
        {
            "name": "Grid Charge",
            "source": ["Grid"],
            "target": ["Battery"],
            "price": as_constant_value(0.05),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_EDIT,
        }
    )

    result = await flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Grid Charge",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULE_NAME: "name_exists"}


def test_endpoint_selector_normalizes_wildcard_and_node_lists(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Policy endpoint ChooseSelector maps none/nodes choices to list or empty string."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar", "Grid"])
    assert sel({"active_choice": CHOICE_NONE}) == ""
    assert sel({"active_choice": CHOICE_NODES, CHOICE_NODES: ["Solar"]}) == ["Solar"]


def test_parse_rule_input_empty_string_price_becomes_none_value() -> None:
    """Empty price string in the form is stored as explicit none pricing."""
    flow = PolicySubentryFlowHandler()
    rule = flow._parse_rule_input(
        {
            CONF_RULE_NAME: "Free flow",
            CONF_PRICE: "",
        }
    )
    assert rule.get("price") == as_none_value()


def test_parse_rule_input_list_price_becomes_entity_value() -> None:
    """Entity list price input maps to schema entity value."""
    flow = PolicySubentryFlowHandler()
    rule = flow._parse_rule_input(
        {
            CONF_RULE_NAME: "Tracked",
            CONF_PRICE: ["sensor.a", "sensor.b"],
        }
    )
    assert rule.get("price") == as_entity_value(["sensor.a", "sensor.b"])


async def test_edit_rule_index_out_of_range_uses_empty_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Invalid editing index falls back to empty suggested values."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow._get_subentry = Mock(return_value=subentry)
    flow._editing_index = 99
    flow._rules = list(existing_rules)

    result = await flow.async_step_edit_rule(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_rule"


def test_endpoint_selector_delegates_to_super_without_active_choice(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Payloads without active_choice are validated by the base ChooseSelector."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar"])
    with pytest.raises(vol.Invalid):
        sel({"unexpected": "shape"})


def test_get_participant_options_skips_invalid_element_type_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Participant options ignore subentries with invalid element_type payloads."""
    invalid_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "not-a-real-type", CONF_NAME: "Broken"}),
        subentry_type="broken",
        title="Broken",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, invalid_subentry)

    flow = _create_flow(hass, hub_entry)
    options = flow._get_participant_options()
    assert "Broken" not in options


async def test_reconfigure_delete_invalid_index_keeps_rules_and_saves(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Deleting an out-of-range index does not mutate rules but still persists current state."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"},
    )

    await flow.async_step_reconfigure(user_input=None)
    result = await flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "5",
            CONF_ACTION: ACTION_DELETE,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert update_data[CONF_RULES] == existing_rules


async def test_edit_rule_valid_input_without_subentry_returns_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """When no subentry is available during edit save, flow returns to form instead of aborting."""
    flow = _create_flow(hass, hub_entry)
    flow._rules = [{"name": "Existing"}]
    flow._editing_index = 0
    flow._get_subentry = Mock(return_value=None)

    result = await flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Renamed",
            CONF_PRICE: 0.01,
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_rule"


# --- Issue 2: Edit rule shows previous values ---


async def test_edit_rule_shows_previous_values_for_source_target(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule with source/target pre-fills the endpoint ChooseSelector format."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow._get_subentry = Mock(return_value=subentry)

    # Load rules and select rule 0 for editing
    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT}
    )

    # Open the edit form without submitting
    result = await flow.async_step_edit_rule(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert _get_suggested_value(result, CONF_SOURCE) == {"active_choice": CHOICE_NODES, CHOICE_NODES: ["Solar"]}
    assert _get_suggested_value(result, CONF_TARGET) == {"active_choice": CHOICE_NODES, CHOICE_NODES: ["Grid"]}


async def test_edit_rule_shows_any_for_missing_source_target(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule without source/target shows 'any' (empty string) as default."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Global Policy",
            "price": as_constant_value(0.05),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow._get_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT}
    )

    result = await flow.async_step_edit_rule(user_input=None)

    assert _get_suggested_value(result, CONF_SOURCE) == ""
    assert _get_suggested_value(result, CONF_TARGET) == ""


async def test_edit_rule_shows_previous_constant_price(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule with constant price pre-fills the price field."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Solar Export",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow._get_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT}
    )

    result = await flow.async_step_edit_rule(user_input=None)

    assert _get_suggested_value(result, CONF_PRICE) == 0.02


async def test_edit_rule_shows_previous_entity_price(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule with entity price pre-fills the entity list."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Tracked",
            "price": as_entity_value(["sensor.price"]),
        },
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow._get_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_reconfigure(
        user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT}
    )

    result = await flow.async_step_edit_rule(user_input=None)

    assert _get_suggested_value(result, CONF_PRICE) == ["sensor.price"]


# --- Issue 4: Enabled/disabled toggle per rule ---


async def test_user_step_stores_enabled_false(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Creating a rule with enabled=False stores it in the rule config."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    await flow.async_step_user(
        user_input={
            CONF_ENABLED: False,
            CONF_RULE_NAME: "Disabled Rule",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
            CONF_PRICE: 0.02,
        }
    )

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_RULES][0].get("enabled") is False


async def test_user_step_stores_enabled_true_by_default(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Creating a rule with enabled=True (default) stores it."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    await flow.async_step_user(
        user_input={
            CONF_ENABLED: True,
            CONF_RULE_NAME: "Active Rule",
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
            CONF_PRICE: 0.02,
        }
    )

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_RULES][0].get("enabled") is True


def test_extract_policy_rules_skips_disabled() -> None:
    """Disabled rules are skipped by extract_policy_rules."""
    config: dict[str, Any] = {
        "rules": [
            {"name": "Active", "source": ["Solar"], "target": ["Grid"], "price": 0.02, "enabled": True},
            {"name": "Disabled", "source": ["Grid"], "target": ["Battery"], "price": 0.05, "enabled": False},
            {"name": "Default", "source": ["Solar"], "target": ["Battery"]},
        ],
    }
    result = extract_policy_rules(config)
    assert len(result) == 2
    assert result[0]["sources"] == ["Solar"]
    assert result[0]["destinations"] == ["Grid"]
    assert result[1]["sources"] == ["Solar"]
    assert result[1]["destinations"] == ["Battery"]


# --- Issue 5: Empty node list normalizes to 'any' ---


def test_endpoint_selector_empty_nodes_normalizes_to_any(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting 'Elements' choice with empty list normalizes to 'any' (empty string)."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar", "Grid"])
    result = sel({"active_choice": CHOICE_NODES, CHOICE_NODES: []})
    assert result == ""

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
from custom_components.haeo.core.schema.elements.inverter import ELEMENT_TYPE as INVERTER_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE as LOAD_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE
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
from custom_components.haeo.core.schema.elements.solar import ELEMENT_TYPE as SOLAR_ELEMENT_TYPE
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.none_value import as_none_value
from custom_components.haeo.flows.elements import policy as policy_flow
from custom_components.haeo.flows.elements.policy import (
    ACTION_DELETE,
    ACTION_EDIT,
    CHOICE_ELEMENTS,
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

    nodes = [
        ("Solar", True, False),
        ("Grid", True, True),
        ("Battery", True, True),
        ("Load", False, True),
    ]
    for name, is_source, is_sink in nodes:
        subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    CONF_ELEMENT_TYPE: NODE_ELEMENT_TYPE,
                    CONF_NAME: name,
                    SECTION_ROLE: {CONF_IS_SOURCE: is_source, CONF_IS_SINK: is_sink},
                }
            ),
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


def _get_selector(result: Any, field_name: str) -> Any:
    """Extract selector instance for a field from a flow result's data_schema."""
    data_schema = result.get("data_schema")
    assert data_schema is not None
    for key, selector in data_schema.schema.items():
        if getattr(key, "schema", None) == field_name:
            return selector
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
            CONF_ENABLED: True,
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
            CONF_ENABLED: True,
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
            CONF_ENABLED: True,
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
            CONF_ENABLED: True,
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Grid"],
            CONF_PRICE: 0.03,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert update_data[CONF_RULES][0]["name"] == "Solar Export Updated"
    assert update_data[CONF_RULES][0]["price"] == as_constant_value(0.03)


async def test_edit_rule_preserves_source_target_when_omitted_from_submission(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule without source/target keeps the existing endpoint values."""
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
            CONF_ENABLED: True,
            CONF_PRICE: 0.03,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert update_data[CONF_RULES][0]["source"] == ["Solar"]
    assert update_data[CONF_RULES][0]["target"] == ["Grid"]
    assert update_data[CONF_RULES][0]["price"] == as_constant_value(0.03)


async def test_edit_rule_updates_only_selected_rule_without_losing_others(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing one rule preserves all other rules and total rule count."""
    existing_rules: list[PolicyRuleConfig] = [
        {
            "name": "Rule A",
            "source": ["Solar"],
            "target": ["Grid"],
            "price": as_constant_value(0.02),
        },
        {
            "name": "Rule B",
            "source": ["Grid"],
            "target": ["Battery"],
            "price": as_constant_value(0.05),
        },
        {
            "name": "Rule C",
            "source": ["Battery"],
            "target": ["Load"],
            "price": as_constant_value(0.01),
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
            CONF_RULE: "1",
            CONF_ACTION: ACTION_EDIT,
        }
    )

    result = await flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Rule B Updated",
            CONF_ENABLED: True,
            CONF_PRICE: 0.07,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    rules = update_data[CONF_RULES]
    assert len(rules) == 3
    assert rules[0] == existing_rules[0]
    assert rules[2] == existing_rules[2]
    assert rules[1]["name"] == "Rule B Updated"
    assert rules[1]["source"] == ["Grid"]
    assert rules[1]["target"] == ["Battery"]
    assert rules[1]["price"] == as_constant_value(0.07)


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


async def test_edit_rule_saved_values_restore_when_reopened(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Saved rule edits appear as defaults when opening edit again."""
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

    # First edit/save pass
    save_flow = _create_flow(hass, hub_entry)
    save_flow.context = {"subentry_id": subentry.subentry_id}
    save_flow._get_reconfigure_subentry = Mock(return_value=subentry)
    save_flow.async_update_and_abort = Mock(
        return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"},
    )

    await save_flow.async_step_reconfigure(user_input=None)
    await save_flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_EDIT,
        }
    )
    await save_flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Solar Export Updated",
            CONF_ENABLED: True,
            CONF_SOURCE: ["Solar"],
            CONF_TARGET: ["Battery"],
            CONF_PRICE: 0.06,
        }
    )

    saved_data = save_flow.async_update_and_abort.call_args.kwargs["data"]
    saved_subentry = _make_policy_subentry(saved_data[CONF_RULES])
    hass.config_entries.async_add_subentry(hub_entry, saved_subentry)

    # Re-open edit using saved values
    reopen_flow = _create_flow(hass, hub_entry)
    reopen_flow.context = {"subentry_id": saved_subentry.subentry_id}
    reopen_flow._get_reconfigure_subentry = Mock(return_value=saved_subentry)
    reopen_flow._get_subentry = Mock(return_value=saved_subentry)

    await reopen_flow.async_step_reconfigure(user_input=None)
    await reopen_flow.async_step_reconfigure(
        user_input={
            CONF_RULE: "0",
            CONF_ACTION: ACTION_EDIT,
        }
    )
    reopen_result = await reopen_flow.async_step_edit_rule(user_input=None)

    assert _get_suggested_value(reopen_result, CONF_RULE_NAME) == "Solar Export Updated"
    assert _get_suggested_value(reopen_result, CONF_SOURCE) == ["Solar"]
    assert _get_suggested_value(reopen_result, CONF_TARGET) == ["Battery"]
    assert _get_suggested_value(reopen_result, CONF_PRICE) == 0.06


async def test_edit_rule_rejects_duplicate_name_preserves_omitted_source_target_defaults(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Validation errors keep previous source/target defaults when omitted from submission."""
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
            CONF_ENABLED: True,
            CONF_PRICE: 0.03,
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULE_NAME: "name_exists"}
    assert _get_suggested_value(result, CONF_SOURCE) == ["Solar"]
    assert _get_suggested_value(result, CONF_TARGET) == ["Grid"]


def test_endpoint_selector_normalizes_wildcard_and_node_lists(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Policy endpoint ChooseSelector maps none/elements choices to list or empty string."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar", "Grid"])
    assert sel({"active_choice": CHOICE_NONE}) == ""
    assert sel({"active_choice": CHOICE_ELEMENTS, CHOICE_ELEMENTS: ["Solar"]}) == ["Solar"]


def test_parse_rule_input_empty_string_price_is_rejected() -> None:
    """Empty price is rejected because policy price is required."""
    flow = PolicySubentryFlowHandler()
    errors: dict[str, str] = {}
    valid = flow._validate_rule(
        {
            CONF_RULE_NAME: "Free flow",
            CONF_ENABLED: True,
            CONF_PRICE: "",
        },
        errors,
    )
    assert not valid
    assert errors == {CONF_PRICE: "required"}


def test_parse_rule_input_list_price_becomes_entity_value() -> None:
    """Entity list price input maps to schema entity value."""
    flow = PolicySubentryFlowHandler()
    rule = flow._parse_rule_input(
        {
            CONF_RULE_NAME: "Tracked",
            CONF_ENABLED: True,
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


def test_endpoint_selector_unknown_active_choice_delegates_to_super(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Unknown active_choice values are delegated to base selector validation."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar"])
    with pytest.raises(vol.Invalid):
        sel({"active_choice": "unknown"})


def test_endpoint_selector_elements_first_when_preferred(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Elements choice is placed first when preferred for restore behavior."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar"], preferred_choice=CHOICE_ELEMENTS)
    choices_keys = list(sel.config["choices"].keys())
    assert choices_keys[0] == CHOICE_ELEMENTS
    assert choices_keys[1] == CHOICE_NONE


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


def test_get_participant_options_skips_subentries_without_registered_adapter(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Subentries with missing adapter registrations are ignored."""
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: SOLAR_ELEMENT_TYPE, CONF_NAME: "SolarNoAdapter"}),
        subentry_type=SOLAR_ELEMENT_TYPE,
        title="SolarNoAdapter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    patched = dict(policy_flow.ELEMENT_TYPES)
    patched.pop(SOLAR_ELEMENT_TYPE, None)
    monkeypatch.setattr(policy_flow, "ELEMENT_TYPES", patched)

    flow = _create_flow(hass, hub_entry)
    options = flow._get_participant_options(can_source=True)
    assert "SolarNoAdapter" not in options


def test_get_participant_options_filters_source_capability(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Source filtering only returns elements whose adapter has can_source=True."""
    # Add a load (sink-only) and solar (source-only) subentry
    for name, etype in [("My Load", LOAD_ELEMENT_TYPE), ("My Solar", SOLAR_ELEMENT_TYPE)]:
        subentry = ConfigSubentry(
            data=MappingProxyType({CONF_ELEMENT_TYPE: etype, CONF_NAME: name}),
            subentry_type=etype,
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    source_options = flow._get_participant_options(can_source=True)
    # Solar adapter has can_source=True
    assert "My Solar" in source_options
    # Load (sink-only) should be excluded
    assert "My Load" not in source_options


def test_get_participant_options_filters_sink_capability(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Sink filtering only returns elements whose adapter has can_sink=True."""
    for name, etype in [("My Load", LOAD_ELEMENT_TYPE), ("My Solar", SOLAR_ELEMENT_TYPE)]:
        subentry = ConfigSubentry(
            data=MappingProxyType({CONF_ELEMENT_TYPE: etype, CONF_NAME: name}),
            subentry_type=etype,
            title=name,
            unique_id=None,
        )
        hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    target_options = flow._get_participant_options(can_sink=True)
    # Load adapter has can_sink=True
    assert "My Load" in target_options
    # Solar (source-only) should be excluded
    assert "My Solar" not in target_options


def test_get_participant_options_excludes_passthrough_elements(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Elements with neither can_source nor can_sink (e.g., inverter) are excluded."""
    inverter_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: INVERTER_ELEMENT_TYPE, CONF_NAME: "Inverter"}),
        subentry_type=INVERTER_ELEMENT_TYPE,
        title="Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, inverter_subentry)

    flow = _create_flow(hass, hub_entry)
    # Inverter excluded from source options
    assert "Inverter" not in flow._get_participant_options(can_source=True)
    # Inverter excluded from sink options
    assert "Inverter" not in flow._get_participant_options(can_sink=True)
    # Inverter excluded from unfiltered options too (neither source nor sink)
    assert "Inverter" not in flow._get_participant_options()


def test_get_participant_options_excludes_junction_nodes(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Node elements with is_source=False and is_sink=False are excluded as junctions."""
    junction_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: NODE_ELEMENT_TYPE,
                CONF_NAME: "Switchboard",
                SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False},
            }
        ),
        subentry_type=NODE_ELEMENT_TYPE,
        title="Switchboard",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, junction_subentry)

    flow = _create_flow(hass, hub_entry)
    assert "Switchboard" not in flow._get_participant_options(can_source=True)
    assert "Switchboard" not in flow._get_participant_options(can_sink=True)
    assert "Switchboard" not in flow._get_participant_options()


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


async def test_reconfigure_edit_invalid_index_shows_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting edit with an invalid index keeps reconfigure form open."""
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
            CONF_RULE: "5",
            CONF_ACTION: ACTION_EDIT,
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "reconfigure"


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
            CONF_ENABLED: True,
            CONF_PRICE: 0.01,
        }
    )

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_rule"


async def test_edit_rule_valid_input_with_invalid_index_returns_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Valid edit submission with invalid index keeps form open."""
    flow = _create_flow(hass, hub_entry)
    flow._rules = [{"name": "Existing", "price": as_constant_value(0.01)}]
    flow._editing_index = 99
    flow._get_subentry = Mock(return_value=None)

    result = await flow.async_step_edit_rule(
        user_input={
            CONF_RULE_NAME: "Renamed",
            CONF_ENABLED: True,
            CONF_PRICE: 0.02,
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
    await flow.async_step_reconfigure(user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})

    # Open the edit form without submitting
    result = await flow.async_step_edit_rule(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert _get_suggested_value(result, CONF_SOURCE) == ["Solar"]
    assert _get_suggested_value(result, CONF_TARGET) == ["Grid"]
    source_selector = _get_selector(result, CONF_SOURCE)
    target_selector = _get_selector(result, CONF_TARGET)
    assert source_selector is not None
    assert target_selector is not None
    assert next(iter(source_selector.config["choices"].keys())) == CHOICE_ELEMENTS
    assert next(iter(target_selector.config["choices"].keys())) == CHOICE_ELEMENTS


async def test_edit_rule_ui_restore_contract_for_elements_endpoints(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """UI restore works by aligning suggested value with first choose choice."""
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
    await flow.async_step_reconfigure(user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})
    result = await flow.async_step_edit_rule(user_input=None)

    source_selector = _get_selector(result, CONF_SOURCE)
    target_selector = _get_selector(result, CONF_TARGET)
    assert source_selector is not None
    assert target_selector is not None
    assert next(iter(source_selector.config["choices"].keys())) == CHOICE_ELEMENTS
    assert next(iter(target_selector.config["choices"].keys())) == CHOICE_ELEMENTS
    assert _get_suggested_value(result, CONF_SOURCE) == ["Solar"]
    assert _get_suggested_value(result, CONF_TARGET) == ["Grid"]


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
    await flow.async_step_reconfigure(user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})

    result = await flow.async_step_edit_rule(user_input=None)

    assert _get_suggested_value(result, CONF_SOURCE) == ""
    assert _get_suggested_value(result, CONF_TARGET) == ""

    source_selector = _get_selector(result, CONF_SOURCE)
    target_selector = _get_selector(result, CONF_TARGET)
    assert source_selector is not None
    assert target_selector is not None
    assert next(iter(source_selector.config["choices"].keys())) == CHOICE_NONE
    assert next(iter(target_selector.config["choices"].keys())) == CHOICE_NONE


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
    await flow.async_step_reconfigure(user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})

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
    await flow.async_step_reconfigure(user_input={CONF_RULE: "0", CONF_ACTION: ACTION_EDIT})

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


def test_endpoint_selector_empty_elements_raises_invalid(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting 'Elements' choice with empty list raises vol.Invalid."""
    flow = _create_flow(hass, hub_entry)
    sel = flow._build_endpoint_selector(["Solar", "Grid"])
    with pytest.raises(vol.Invalid):
        sel({"active_choice": CHOICE_ELEMENTS, CHOICE_ELEMENTS: []})


def test_rule_to_defaults_enabled_always_present() -> None:
    """Enabled is always present in defaults, defaulting to True when missing."""
    flow = PolicySubentryFlowHandler()
    defaults = flow._rule_to_defaults({"name": "Test"})
    assert defaults[CONF_ENABLED] is True

    defaults_disabled = flow._rule_to_defaults({"name": "Test", "enabled": False})
    assert defaults_disabled[CONF_ENABLED] is False


def test_rule_to_defaults_ignores_legacy_none_price() -> None:
    """Legacy none pricing does not add a price default."""
    flow = PolicySubentryFlowHandler()
    defaults = flow._rule_to_defaults({"name": "Test", "price": as_none_value()})
    assert CONF_PRICE not in defaults


def test_rule_to_edit_input_maps_legacy_none_price_to_empty_string() -> None:
    """Legacy none pricing maps to empty string for form-compatible merged input."""
    flow = PolicySubentryFlowHandler()
    input_values = flow._rule_to_edit_input({"name": "Test", "price": as_none_value()})
    assert input_values[CONF_PRICE] == ""


def test_parse_rule_input_stores_enabled() -> None:
    """Enabled field is always stored in the rule."""
    flow = PolicySubentryFlowHandler()
    rule = flow._parse_rule_input({CONF_RULE_NAME: "Test", CONF_ENABLED: True})
    assert rule.get("enabled") is True

    rule_disabled = flow._parse_rule_input({CONF_RULE_NAME: "Test", CONF_ENABLED: False})
    assert rule_disabled.get("enabled") is False


@pytest.mark.parametrize(
    "price_input",
    [
        None,
        [],
    ],
)
def test_validate_rule_requires_non_empty_price(price_input: Any) -> None:
    """Rule validation rejects missing or empty list price input."""
    flow = PolicySubentryFlowHandler()
    errors: dict[str, str] = {}
    valid = flow._validate_rule(
        {
            CONF_RULE_NAME: "Test",
            CONF_ENABLED: True,
            CONF_PRICE: price_input,
        },
        errors,
    )
    assert not valid
    assert errors == {CONF_PRICE: "required"}

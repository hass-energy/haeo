"""Tests for the policy element multi-step config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE as NODE_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_RULE_NAME,
    CONF_RULES,
    CONF_SOURCE,
    CONF_TARGET,
    WILDCARD,
)
from custom_components.haeo.core.schema.elements.policy import ELEMENT_TYPE as POLICY_ELEMENT_TYPE
from custom_components.haeo.flows.elements.policy import (
    ACTION_ADD,
    ACTION_DONE,
    CONF_ACTION,
    CONF_DELETE,
    POLICIES_TITLE,
    PolicySubentryFlowHandler,
)


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

    # Add participant nodes so the policy source/target dropdowns are populated
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


def _make_policy_subentry(rules: list[dict[str, Any]]) -> ConfigSubentry:
    """Create a policy subentry with the provided rules."""
    data = MappingProxyType({
        CONF_ELEMENT_TYPE: POLICY_ELEMENT_TYPE,
        CONF_NAME: POLICIES_TITLE,
        CONF_RULES: rules,
    })
    return ConfigSubentry(
        data=data,
        subentry_type=POLICY_ELEMENT_TYPE,
        title=POLICIES_TITLE,
        unique_id=None,
    )


# --- User step (adding new Policies subentry) ---


async def test_user_step_shows_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """First call to async_step_user shows the rule form."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_user_step_creates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a valid rule creates the Policies subentry."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    result = await flow.async_step_user(user_input={
        CONF_RULE_NAME: "Solar Export",
        CONF_SOURCE: "Solar",
        CONF_TARGET: "Grid",
        CONF_PRICE_SOURCE_TARGET: 0.02,
    })

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_ELEMENT_TYPE] == POLICY_ELEMENT_TYPE
    assert created_data[CONF_NAME] == POLICIES_TITLE
    assert len(created_data[CONF_RULES]) == 1
    assert created_data[CONF_RULES][0]["name"] == "Solar Export"


async def test_user_step_rejects_missing_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a rule without a name shows an error."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(user_input={
        CONF_RULE_NAME: "",
        CONF_SOURCE: "Solar",
        CONF_TARGET: "Grid",
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULE_NAME: "missing_name"}


async def test_user_step_rejects_same_source_target(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting source == target (non-wildcard) shows an error."""
    flow = _create_flow(hass, hub_entry)

    result = await flow.async_step_user(user_input={
        CONF_RULE_NAME: "Self Loop",
        CONF_SOURCE: "Solar",
        CONF_TARGET: "Solar",
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {"base": "source_target_same"}


async def test_user_step_allows_wildcard_same(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Wildcard source == wildcard target is allowed."""
    flow = _create_flow(hass, hub_entry)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": POLICIES_TITLE, "data": {}},
    )

    result = await flow.async_step_user(user_input={
        CONF_RULE_NAME: "Global Policy",
        CONF_SOURCE: WILDCARD,
        CONF_TARGET: WILDCARD,
        CONF_PRICE_SOURCE_TARGET: 0.05,
    })

    assert result.get("type") == FlowResultType.CREATE_ENTRY


# --- Reconfigure step (existing Policies subentry) ---


async def test_reconfigure_shows_menu(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure loads existing rules and shows the menu."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "menu"


async def test_menu_add_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting 'Add' from the menu shows the add_rule form."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)

    result = await flow.async_step_menu(user_input={CONF_ACTION: ACTION_ADD})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "add_rule"


async def test_add_rule_returns_to_menu(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting a valid new rule returns to the menu."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_menu(user_input={CONF_ACTION: ACTION_ADD})

    result = await flow.async_step_add_rule(user_input={
        CONF_RULE_NAME: "Grid Charge",
        CONF_SOURCE: "Grid",
        CONF_TARGET: "Battery",
        CONF_PRICE_SOURCE_TARGET: 0.05,
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "menu"
    assert len(flow._rules) == 2


async def test_add_rule_rejects_duplicate_name(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Adding a rule with a name that already exists shows an error."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_menu(user_input={CONF_ACTION: ACTION_ADD})

    result = await flow.async_step_add_rule(user_input={
        CONF_RULE_NAME: "Solar Export",
        CONF_SOURCE: "Grid",
        CONF_TARGET: "Battery",
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULE_NAME: "name_exists"}


async def test_menu_edit_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting a rule index from the menu shows the edit form."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)

    result = await flow.async_step_menu(user_input={CONF_ACTION: "0"})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_rule"


async def test_edit_rule_updates_and_returns_to_menu(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Editing a rule updates it and returns to the menu."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_menu(user_input={CONF_ACTION: "0"})

    result = await flow.async_step_edit_rule(user_input={
        CONF_RULE_NAME: "Solar Export Updated",
        CONF_SOURCE: "Solar",
        CONF_TARGET: "Grid",
        CONF_PRICE_SOURCE_TARGET: 0.03,
        CONF_DELETE: False,
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "menu"
    assert flow._rules[0]["name"] == "Solar Export Updated"
    assert flow._rules[0].get("price_source_target") == 0.03


async def test_edit_rule_delete(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Checking the delete checkbox removes the rule."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
        {"name": "Grid Charge", "source": "Grid", "target": "Battery", "price_source_target": 0.05},
    ]
    subentry = _make_policy_subentry(existing_rules)
    hass.config_entries.async_add_subentry(hub_entry, subentry)

    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)

    await flow.async_step_reconfigure(user_input=None)
    await flow.async_step_menu(user_input={CONF_ACTION: "0"})

    result = await flow.async_step_edit_rule(user_input={
        CONF_RULE_NAME: "Solar Export",
        CONF_SOURCE: "Solar",
        CONF_TARGET: "Grid",
        CONF_DELETE: True,
    })

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "menu"
    assert len(flow._rules) == 1
    assert flow._rules[0]["name"] == "Grid Charge"


async def test_menu_done_saves(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting 'Save and close' updates the subentry."""
    existing_rules = [
        {"name": "Solar Export", "source": "Solar", "target": "Grid", "price_source_target": 0.02},
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

    result = await flow.async_step_menu(user_input={CONF_ACTION: ACTION_DONE})

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"
    update_data = flow.async_update_and_abort.call_args.kwargs["data"]
    assert update_data[CONF_RULES] == existing_rules

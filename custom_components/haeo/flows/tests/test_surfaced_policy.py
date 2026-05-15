"""Tests for surfaced policy rule management utilities."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo import _cleanup_policy_rules
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CHARGE_COST,
    CONF_CONFIGURE_PARTITIONS,
    CONF_DISCHARGE_COST,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.battery import SURFACED_PRICE_HINTS as BATTERY_SURFACED_PRICE_HINTS
from custom_components.haeo.core.schema.elements.load import (
    CONF_CONSUMPTION_COST,
    CONF_CURTAILMENT,
    CONF_FORECAST,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
)
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE as LOAD_ELEMENT_TYPE
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
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_surfaced_input_fields
from custom_components.haeo.flows.conftest import create_flow
from custom_components.haeo.flows.surfaced_policy import (
    POLICIES_TITLE,
    build_surfaced_defaults,
    find_policy_subentry,
    find_surfaced_rule,
    form_value_to_price,
    get_policy_rules,
    price_to_form_value,
    save_surfaced_rule,
)

# --- Helper functions ---


def _add_policy_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    rules: list[dict[str, Any]],
) -> ConfigSubentry:
    """Add a policy subentry with the given rules."""
    data = MappingProxyType(
        {
            CONF_ELEMENT_TYPE: str(POLICY_ELEMENT_TYPE),
            CONF_NAME: POLICIES_TITLE,
            CONF_RULES: rules,
        }
    )
    subentry = ConfigSubentry(
        data=data,
        subentry_type=str(POLICY_ELEMENT_TYPE),
        title=POLICIES_TITLE,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _get_rules(hub_entry: MockConfigEntry) -> list[PolicyRuleConfig]:
    """Get all policy rules from the hub entry."""
    return get_policy_rules(hub_entry)


# --- find_policy_subentry tests ---


def test_find_policy_subentry_returns_none_when_absent(
    hub_entry: MockConfigEntry,
) -> None:
    """Returns None when no policy subentry exists."""
    assert find_policy_subentry(hub_entry) is None


def test_find_policy_subentry_returns_subentry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Returns the policy subentry when present."""
    subentry = _add_policy_subentry(hass, hub_entry, [])
    result = find_policy_subentry(hub_entry)
    assert result is not None
    assert result.subentry_id == subentry.subentry_id


# --- get_policy_rules tests ---


def test_get_policy_rules_empty_when_no_subentry(
    hub_entry: MockConfigEntry,
) -> None:
    """Returns empty list when no policy subentry exists."""
    assert get_policy_rules(hub_entry) == []


def test_get_policy_rules_returns_rules(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Returns the rule list from the policy subentry."""
    rules = [{"name": "test", "price": as_constant_value(0.1)}]
    _add_policy_subentry(hass, hub_entry, rules)
    result = get_policy_rules(hub_entry)
    assert len(result) == 1
    assert result[0]["name"] == "test"


# --- find_surfaced_rule tests ---


@pytest.mark.parametrize(
    ("rules", "source", "target", "expected_index"),
    [
        pytest.param([], None, ["Battery"], None, id="empty_rules"),
        pytest.param(
            [{"name": "r1", "target": ["Battery"], "price": as_constant_value(0.1)}],
            None,
            ["Battery"],
            0,
            id="wildcard_to_element",
        ),
        pytest.param(
            [{"name": "r1", "source": ["Battery"], "price": as_constant_value(0.1)}],
            ["Battery"],
            None,
            0,
            id="element_to_wildcard",
        ),
        pytest.param(
            [
                {"name": "r1", "source": ["Other"], "price": as_constant_value(0.1)},
                {"name": "r2", "target": ["Battery"], "price": as_constant_value(0.2)},
            ],
            None,
            ["Battery"],
            1,
            id="second_rule_matches",
        ),
        pytest.param(
            [{"name": "r1", "source": ["A"], "target": ["B"], "price": as_constant_value(0.1)}],
            None,
            ["B"],
            None,
            id="both_sides_set_no_match",
        ),
    ],
)
def test_find_surfaced_rule(
    rules: list[PolicyRuleConfig],
    source: list[str] | None,
    target: list[str] | None,
    expected_index: int | None,
) -> None:
    """Finds the correct rule index by endpoint pattern."""
    assert find_surfaced_rule(rules, source=source, target=target) == expected_index


# --- price_to_form_value / form_value_to_price round-trip tests ---


@pytest.mark.parametrize(
    ("price", "expected_form_value"),
    [
        pytest.param(None, None, id="none"),
        pytest.param(as_constant_value(0.5), 0.5, id="constant"),
        pytest.param(as_entity_value(["sensor.price"]), ["sensor.price"], id="entity"),
    ],
)
def test_price_to_form_value(price: Any, expected_form_value: Any) -> None:
    """Converts stored prices to form field values."""
    assert price_to_form_value(price) == expected_form_value


@pytest.mark.parametrize(
    ("form_value", "expected_price"),
    [
        pytest.param(None, None, id="none"),
        pytest.param("", None, id="empty_string"),
        pytest.param([], None, id="empty_list"),
        pytest.param(0.5, as_constant_value(0.5), id="float"),
        pytest.param(1, as_constant_value(1.0), id="int"),
        pytest.param(["sensor.price"], as_entity_value(["sensor.price"]), id="entity_list"),
    ],
)
def test_form_value_to_price(form_value: Any, expected_price: Any) -> None:
    """Converts form field values back to stored prices."""
    assert form_value_to_price(form_value) == expected_price


# --- save_surfaced_rule tests ---


def test_save_creates_policy_subentry_and_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Creates a policy subentry and rule when none exist."""
    save_surfaced_rule(
        hass,
        hub_entry,
        rule_name="Battery charge cost",
        source=None,
        target=["Battery"],
        price=as_constant_value(-0.001),
    )
    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0]["name"] == "Battery charge cost"
    assert rules[0].get("target") == ["Battery"]
    assert rules[0]["price"] == as_constant_value(-0.001)
    assert "source" not in rules[0]


def test_save_updates_existing_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Updates an existing rule in place."""
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "old name", "target": ["Battery"], "price": as_constant_value(0.0)},
        ],
    )
    save_surfaced_rule(
        hass,
        hub_entry,
        rule_name="new name",
        source=None,
        target=["Battery"],
        price=as_constant_value(0.5),
    )
    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0]["name"] == "new name"
    assert rules[0]["price"] == as_constant_value(0.5)


def test_save_appends_new_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Appends a new rule alongside existing rules."""
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "existing", "source": ["Other"], "price": as_constant_value(0.1)},
        ],
    )
    save_surfaced_rule(
        hass,
        hub_entry,
        rule_name="new",
        source=None,
        target=["Battery"],
        price=as_constant_value(0.2),
    )
    rules = _get_rules(hub_entry)
    assert len(rules) == 2


def test_save_with_none_price_deletes_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Passing price=None deletes the matching rule."""
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "to delete", "target": ["Battery"], "price": as_constant_value(0.1)},
            {"name": "keep", "source": ["X"], "price": as_constant_value(0.2)},
        ],
    )
    save_surfaced_rule(
        hass,
        hub_entry,
        rule_name="to delete",
        source=None,
        target=["Battery"],
        price=None,
    )
    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0]["name"] == "keep"


def test_save_with_none_price_no_match_is_noop(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Passing price=None when no matching rule exists does nothing."""
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "keep", "source": ["X"], "price": as_constant_value(0.2)},
        ],
    )
    save_surfaced_rule(
        hass,
        hub_entry,
        rule_name="nonexistent",
        source=None,
        target=["Battery"],
        price=None,
    )
    rules = _get_rules(hub_entry)
    assert len(rules) == 1


# --- build_surfaced_defaults tests ---


def test_defaults_for_new_element(
    hub_entry: MockConfigEntry,
) -> None:
    """New elements get spec default values."""
    surfaced_fields = get_surfaced_input_fields(BATTERY_ELEMENT_TYPE)
    defaults = build_surfaced_defaults(hub_entry, None, BATTERY_SURFACED_PRICE_HINTS, surfaced_fields)
    assert defaults[CONF_CHARGE_COST] == -0.001
    assert defaults[CONF_DISCHARGE_COST] == 0.0


def test_defaults_for_existing_element_with_rules(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Existing elements read current prices from policy rules."""
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "charge", "target": ["Battery"], "price": as_constant_value(0.5)},
            {"name": "discharge", "source": ["Battery"], "price": as_entity_value(["sensor.cost"])},
        ],
    )
    defaults = build_surfaced_defaults(
        hub_entry, "Battery", BATTERY_SURFACED_PRICE_HINTS, get_surfaced_input_fields(BATTERY_ELEMENT_TYPE)
    )
    assert defaults[CONF_CHARGE_COST] == 0.5
    assert defaults[CONF_DISCHARGE_COST] == ["sensor.cost"]


def test_defaults_for_existing_element_without_rules(
    hub_entry: MockConfigEntry,
) -> None:
    """Existing elements without matching rules default to none."""
    defaults = build_surfaced_defaults(
        hub_entry, "Battery", BATTERY_SURFACED_PRICE_HINTS, get_surfaced_input_fields(BATTERY_ELEMENT_TYPE)
    )
    assert CONF_CHARGE_COST not in defaults
    assert CONF_DISCHARGE_COST not in defaults


# --- Battery flow integration tests ---


def _wrap_battery_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Wrap battery user input into sectioned form data."""
    common = {key: user_input[key] for key in (CONF_NAME, CONF_CONNECTION) if key in user_input}
    pricing: dict[str, Any] = {}
    for key in (CONF_SALVAGE_VALUE, CONF_CHARGE_COST, CONF_DISCHARGE_COST):
        if key in user_input:
            pricing[key] = user_input[key]
    pricing.setdefault(CONF_SALVAGE_VALUE, 0.0)

    return {
        **common,
        SECTION_STORAGE: {
            key: user_input[key] for key in (CONF_CAPACITY, CONF_INITIAL_CHARGE_PERCENTAGE) if key in user_input
        },
        SECTION_LIMITS: {
            key: user_input[key]
            for key in (CONF_MIN_CHARGE_PERCENTAGE, CONF_MAX_CHARGE_PERCENTAGE)
            if key in user_input
        },
        SECTION_POWER_LIMITS: {
            key: user_input[key]
            for key in (CONF_MAX_POWER_SOURCE_TARGET, CONF_MAX_POWER_TARGET_SOURCE)
            if key in user_input
        },
        SECTION_PRICING: pricing,
        SECTION_EFFICIENCY: {
            key: user_input[key]
            for key in (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE)
            if key in user_input
        },
    }


def _base_battery_input() -> dict[str, Any]:
    """Return minimal valid battery input."""
    return {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: 0.95,
        CONF_EFFICIENCY_TARGET_SOURCE: 0.95,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
        CONF_CONFIGURE_PARTITIONS: False,
    }


async def test_battery_flow_creates_surfaced_rules(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Battery flow creates charge and discharge cost rules in policy subentry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, BATTERY_ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}}
    )

    user_input = _base_battery_input()
    user_input[CONF_CHARGE_COST] = 0.05
    user_input[CONF_DISCHARGE_COST] = 0.02

    result = await flow.async_step_user(user_input=_wrap_battery_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    rules = _get_rules(hub_entry)
    assert len(rules) == 2

    # Verify charge cost rule (* → Test Battery)
    charge_rule = next(r for r in rules if "charge" in r["name"].lower())
    assert "source" not in charge_rule
    assert charge_rule.get("target") == ["Test Battery"]
    assert charge_rule["price"] == as_constant_value(0.05)

    # Verify discharge cost rule (Test Battery → *)
    discharge_rule = next(r for r in rules if "discharge" in r["name"].lower())
    assert discharge_rule.get("source") == ["Test Battery"]
    assert "target" not in discharge_rule
    assert discharge_rule["price"] == as_constant_value(0.02)


async def test_battery_flow_none_cost_skips_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Battery flow with None cost values doesn't create rules."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, BATTERY_ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}}
    )

    user_input = _base_battery_input()
    user_input[CONF_CHARGE_COST] = None
    user_input[CONF_DISCHARGE_COST] = None

    result = await flow.async_step_user(user_input=_wrap_battery_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    rules = _get_rules(hub_entry)
    assert len(rules) == 0


async def test_battery_flow_excludes_surfaced_fields_from_config(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Surfaced price fields are not stored in battery subentry config."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, BATTERY_ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}}
    )

    user_input = _base_battery_input()
    user_input[CONF_CHARGE_COST] = 0.05
    user_input[CONF_DISCHARGE_COST] = 0.02

    await flow.async_step_user(user_input=_wrap_battery_input(user_input))

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    pricing = created_data.get(SECTION_PRICING, {})
    assert CONF_CHARGE_COST not in pricing
    assert CONF_DISCHARGE_COST not in pricing


async def test_battery_flow_entity_cost_creates_entity_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Battery flow with entity value creates entity-based rule."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, BATTERY_ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}}
    )

    user_input = _base_battery_input()
    user_input[CONF_CHARGE_COST] = ["sensor.cost"]
    user_input[CONF_DISCHARGE_COST] = None

    await flow.async_step_user(user_input=_wrap_battery_input(user_input))

    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0]["price"] == as_entity_value(["sensor.cost"])


# --- Load flow integration tests ---


def _wrap_load_input(flat: dict[str, Any]) -> dict[str, Any]:
    """Wrap flat load input values into sectioned config."""
    curtailment: dict[str, Any] = {}
    for key in (CONF_CURTAILMENT, CONF_CONSUMPTION_COST):
        if key in flat:
            curtailment[key] = flat[key]
    return {
        CONF_NAME: flat[CONF_NAME],
        CONF_CONNECTION: flat[CONF_CONNECTION],
        SECTION_FORECAST: {
            CONF_FORECAST: flat[CONF_FORECAST],
        },
        SECTION_CURTAILMENT: curtailment,
    }


async def test_load_flow_creates_consumption_cost_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Load flow creates consumption cost rule in policy subentry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, LOAD_ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Load", "data": {}})

    user_input = _wrap_load_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.load_forecast"],
            CONF_CURTAILMENT: False,
            CONF_CONSUMPTION_COST: 0.15,
        }
    )
    result = await flow.async_step_user(user_input=user_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0].get("target") == ["Test Load"]
    assert "source" not in rules[0]
    assert rules[0]["price"] == as_constant_value(0.15)


async def test_load_flow_none_cost_skips_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Load flow with None consumption cost doesn't create a rule."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, LOAD_ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Load", "data": {}})

    user_input = _wrap_load_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.load_forecast"],
            CONF_CURTAILMENT: False,
            CONF_CONSUMPTION_COST: None,
        }
    )
    result = await flow.async_step_user(user_input=user_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    assert _get_rules(hub_entry) == []


async def test_load_flow_excludes_surfaced_fields_from_config(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Surfaced price fields are not stored in load subentry config."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, LOAD_ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Load", "data": {}})

    user_input = _wrap_load_input(
        {
            CONF_NAME: "Test Load",
            CONF_CONNECTION: "main_bus",
            CONF_FORECAST: ["sensor.load_forecast"],
            CONF_CURTAILMENT: False,
            CONF_CONSUMPTION_COST: 0.15,
        }
    )
    await flow.async_step_user(user_input=user_input)

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    curtailment = created_data.get(SECTION_CURTAILMENT, {})
    assert CONF_CONSUMPTION_COST not in curtailment


# --- Policy flow duplicate prevention tests ---


async def test_policy_flow_blocks_duplicate_rule(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Policy flow prevents creating rules with the same source/target as an existing rule."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "MyBattery", str(BATTERY_ELEMENT_TYPE))

    # Add an existing rule with * → MyBattery
    _add_policy_subentry(
        hass,
        hub_entry,
        [{"name": "existing", "target": ["MyBattery"], "price": as_constant_value(0.1)}],
    )

    flow = create_flow(hass, hub_entry, POLICY_ELEMENT_TYPE)

    # Try to create a rule with the same pattern
    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "duplicate",
            CONF_ENABLED: True,
            CONF_SOURCE: [],
            CONF_TARGET: ["MyBattery"],
            CONF_PRICE: 0.2,
        }
    )
    assert result.get("type") == FlowResultType.FORM
    errors = result.get("errors", {})
    assert errors.get("base") == "duplicate_rule"


async def test_policy_flow_allows_unique_pattern(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Policy flow allows rules with a unique source/target pattern."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    add_participant(hass, hub_entry, "MyBattery", str(BATTERY_ELEMENT_TYPE))

    flow = create_flow(hass, hub_entry, POLICY_ELEMENT_TYPE)
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Policies", "data": {}})

    result = await flow.async_step_user(
        user_input={
            CONF_RULE_NAME: "normal rule",
            CONF_ENABLED: True,
            CONF_SOURCE: ["main_bus"],
            CONF_TARGET: ["MyBattery"],
            CONF_PRICE: 0.1,
        }
    )
    assert result.get("type") == FlowResultType.CREATE_ENTRY


# --- Cleanup tests ---


def test_cleanup_removes_orphaned_rules(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Cleanup removes rules for elements that no longer exist."""
    add_participant(hass, hub_entry, "Battery1", str(BATTERY_ELEMENT_TYPE))
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "charge", "target": ["Battery1"], "price": as_constant_value(0.1)},
            {"name": "discharge", "source": ["Battery1"], "price": as_constant_value(0.2)},
            {"name": "load charge", "target": ["DeletedLoad"], "price": as_constant_value(0.3)},
            {"name": "deleted discharge", "source": ["DeletedBattery"], "price": as_constant_value(0.4)},
        ],
    )

    _cleanup_policy_rules(hass, hub_entry)

    rules = _get_rules(hub_entry)
    assert len(rules) == 2
    names = {r["name"] for r in rules}
    assert "charge" in names
    assert "discharge" in names


def test_cleanup_strips_deleted_from_multi_element_rules(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Cleanup strips deleted names from multi-element source/target lists."""
    add_participant(hass, hub_entry, "A", str(BATTERY_ELEMENT_TYPE))
    add_participant(hass, hub_entry, "C", str(LOAD_ELEMENT_TYPE))
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "multi", "source": ["A", "B"], "target": ["C"], "price": as_constant_value(0.5)},
        ],
    )

    _cleanup_policy_rules(hass, hub_entry)

    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0].get("source") == ["A"]
    assert rules[0].get("target") == ["C"]


def test_cleanup_removes_rule_when_either_side_empty(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Cleanup removes rules where source or target had elements but became empty."""
    add_participant(hass, hub_entry, "Alive", str(BATTERY_ELEMENT_TYPE))
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "source gone", "source": ["Gone"], "target": ["Alive"], "price": as_constant_value(0.1)},
            {"name": "target gone", "source": ["Alive"], "target": ["Gone"], "price": as_constant_value(0.2)},
            {"name": "both gone", "source": ["Gone1"], "target": ["Gone2"], "price": as_constant_value(0.3)},
        ],
    )

    _cleanup_policy_rules(hass, hub_entry)

    rules = _get_rules(hub_entry)
    assert len(rules) == 0


def test_cleanup_noop_when_no_policy(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Cleanup does nothing when no policy subentry exists."""
    _cleanup_policy_rules(hass, hub_entry)
    assert find_policy_subentry(hub_entry) is None


def test_cleanup_deduplicates_rules_after_stripping(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Cleanup removes duplicate rules that arise from stripping deleted elements."""
    add_participant(hass, hub_entry, "A", str(BATTERY_ELEMENT_TYPE))
    add_participant(hass, hub_entry, "C", str(LOAD_ELEMENT_TYPE))
    _add_policy_subentry(
        hass,
        hub_entry,
        [
            {"name": "first", "source": ["A"], "target": ["C"], "price": as_constant_value(0.1)},
            {"name": "second", "source": ["A", "B"], "target": ["C"], "price": as_constant_value(0.2)},
        ],
    )

    _cleanup_policy_rules(hass, hub_entry)

    rules = _get_rules(hub_entry)
    assert len(rules) == 1
    assert rules[0]["name"] == "first"

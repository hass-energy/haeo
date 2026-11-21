"""Tests for the policy element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry, SubentryFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.adapters.elements.policy import extract_policy_rules
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.constant_value import as_constant_value
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.battery import ELEMENT_TYPE as BATTERY_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.inverter import ELEMENT_TYPE as INVERTER_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.load import ELEMENT_TYPE as LOAD_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.node import CONF_IS_SINK, CONF_IS_SOURCE, SECTION_ROLE
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE as NODE_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.policy import CONF_RULES, PolicyConfigData, PolicyRuleConfig
from custom_components.haeo.core.schema.elements.policy import ELEMENT_TYPE as POLICY_ELEMENT_TYPE
from custom_components.haeo.core.schema.elements.solar import ELEMENT_TYPE as SOLAR_ELEMENT_TYPE
from custom_components.haeo.core.schema.entity_value import as_entity_value
from custom_components.haeo.core.schema.none_value import as_none_value
from custom_components.haeo.flows.elements.policy import PolicySubentryFlowHandler
from custom_components.haeo.flows.policy_rules_selector import PolicyRulesSelector, PolicyRuleValue
from custom_components.haeo.flows.surfaced_policy import POLICIES_TITLE


@pytest.fixture
def hub_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a hub config entry with node participants that source, sink, or both."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB},
        entry_id="test_hub_id",
    )
    entry.add_to_hass(hass)
    for name, is_source, is_sink in (
        ("Solar", True, False),
        ("Grid", True, True),
        ("Battery", True, True),
        ("Load", False, True),
    ):
        _add_element(
            hass,
            entry,
            name,
            NODE_ELEMENT_TYPE,
            {SECTION_ROLE: {CONF_IS_SOURCE: is_source, CONF_IS_SINK: is_sink}},
        )
    return entry


def _add_element(
    hass: HomeAssistant, entry: MockConfigEntry, name: str, element_type: str, data: dict[str, object] | None = None
) -> ConfigSubentry:
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: element_type, CONF_NAME: name, **(data or {})}),
        subentry_type=element_type,
        title=name,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


def _add_policies(hass: HomeAssistant, entry: MockConfigEntry, rules: list[PolicyRuleConfig]) -> ConfigSubentry:
    return _add_element(hass, entry, POLICIES_TITLE, POLICY_ELEMENT_TYPE, {CONF_RULES: rules})


def _create_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> PolicySubentryFlowHandler:
    """Create a policy flow handler wired to the test hub."""
    flow = PolicySubentryFlowHandler()
    flow.hass = hass
    flow.handler = (hub_entry.entry_id, POLICY_ELEMENT_TYPE)
    flow.context = {"source": "user"}
    return flow


def _reconfigure_flow(
    hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry
) -> PolicySubentryFlowHandler:
    flow = _create_flow(hass, hub_entry)
    flow.context = {"subentry_id": subentry.subentry_id, "source": "reconfigure"}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    return flow


def _rule(
    name: str,
    *,
    source: list[str] | None = None,
    target: list[str] | None = None,
    price: object = None,
    enabled: bool = True,
) -> PolicyRuleValue:
    """Return a rule as the rules element submits it."""
    return {
        "name": name,
        "enabled": enabled,
        "source": source or [],
        "target": target or [],
        "price": as_constant_value(0.02) if price is None else price,  # type: ignore[typeddict-item]
    }


def _shown_rules(result: SubentryFlowResult) -> list[PolicyRuleValue]:
    """Return the rules a shown form opens with."""
    data_schema = result.get("data_schema")
    assert data_schema is not None
    key = next(key for key in data_schema.schema if key.schema == CONF_RULES)
    return key.description["suggested_value"]


def _selector(result: SubentryFlowResult) -> PolicyRulesSelector:
    data_schema = result.get("data_schema")
    assert data_schema is not None
    selector = next(selector for key, selector in data_schema.schema.items() if key.schema == CONF_RULES)
    assert isinstance(selector, PolicyRulesSelector)
    return selector


ON = as_constant_value(value=True)
SOLAR_EXPORT: PolicyRuleConfig = {
    "name": "Solar Export",
    "enabled": as_constant_value(value=True),
    "source": ["Solar"],
    "target": ["Grid"],
    "price": as_constant_value(0.02),
}
GRID_CHARGE: PolicyRuleConfig = {
    "name": "Grid Charge",
    "enabled": as_constant_value(value=False),
    "source": ["Grid"],
    "price": as_entity_value(["sensor.grid_price"]),
}


async def test_adding_the_first_rule_opens_a_new_rule_and_creates_the_policies(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """With no policies yet, the form opens with one blank rule, and saving it creates the Policies subentry."""
    flow = _create_flow(hass, hub_entry)

    shown = await flow.async_step_user(user_input=None)

    assert shown.get("step_id") == "user"
    assert _shown_rules(shown) == [
        {"name": "Rule 1", "enabled": True, "source": [], "target": [], "price": as_none_value()}
    ]

    result = await flow.async_step_user(
        user_input={CONF_RULES: [_rule("Solar Export", source=["Solar"], target=["Grid"])]}
    )

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert result.get("data") == {
        CONF_ELEMENT_TYPE: POLICY_ELEMENT_TYPE,
        CONF_NAME: POLICIES_TITLE,
        CONF_RULES: [SOLAR_EXPORT],
    }


async def test_adding_a_rule_opens_the_stored_rules_with_a_new_one_and_saves_into_the_policies(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """With policies already stored, adding opens them all plus a new rule, and saves into the one subentry."""
    _add_policies(hass, hub_entry, [SOLAR_EXPORT, {**GRID_CHARGE, "name": "Rule 2"}])
    flow = _create_flow(hass, hub_entry)

    shown = await flow.async_step_user(user_input=None)

    assert [rule["name"] for rule in _shown_rules(shown)] == ["Solar Export", "Rule 2", "Rule 3"]

    result = await flow.async_step_user(
        user_input={
            CONF_RULES: [
                _rule("Solar Export", source=["Solar"], target=["Grid"]),
                _rule("Battery Wear", source=["Battery"], price=as_constant_value(0.01)),
            ]
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    policies = [sub for sub in hub_entry.subentries.values() if sub.subentry_type == POLICY_ELEMENT_TYPE]
    assert len(policies) == 1
    assert [rule["name"] for rule in policies[0].data[CONF_RULES]] == ["Solar Export", "Battery Wear"]


async def test_reconfigure_opens_the_stored_rules_as_the_editor_shows_them(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Each stored rule opens with its on state as a bool, its ends as lists, empty for any, and its price."""
    subentry = _add_policies(hass, hub_entry, [SOLAR_EXPORT, GRID_CHARGE])

    shown = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(user_input=None)

    assert shown.get("step_id") == "reconfigure"
    assert _shown_rules(shown) == [
        _rule("Solar Export", source=["Solar"], target=["Grid"]),
        _rule("Grid Charge", source=["Grid"], price=as_entity_value(["sensor.grid_price"]), enabled=False),
    ]


@pytest.mark.parametrize(
    ("submitted", "stored"),
    [
        pytest.param(
            [_rule("Solar Export", source=["Solar"], target=["Grid"], enabled=False)],
            [{**SOLAR_EXPORT, "enabled": as_constant_value(value=False)}],
            id="turned_off_and_one_removed",
        ),
        pytest.param(
            [_rule("Export", target=["Grid"]), _rule("Grid Charge", source=["Grid"], price=as_constant_value(0.5))],
            [
                {
                    "name": "Export",
                    "enabled": as_constant_value(value=True),
                    "target": ["Grid"],
                    "price": as_constant_value(0.02),
                },
                {
                    "name": "Grid Charge",
                    "enabled": as_constant_value(value=True),
                    "source": ["Grid"],
                    "price": as_constant_value(0.5),
                },
            ],
            id="edited_with_an_end_left_any",
        ),
        pytest.param([], [], id="all_removed"),
    ],
)
async def test_reconfigure_saves_the_rules_as_edited(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    submitted: list[PolicyRuleValue],
    stored: list[PolicyRuleConfig],
) -> None:
    """Saving stores each rule's on state as a constant and leaves out an end naming no elements."""
    subentry = _add_policies(hass, hub_entry, [SOLAR_EXPORT, GRID_CHARGE])

    result = await _reconfigure_flow(hass, hub_entry, subentry).async_step_reconfigure(
        user_input={CONF_RULES: submitted}
    )

    assert result.get("type") == FlowResultType.ABORT
    assert hub_entry.subentries[subentry.subentry_id].data[CONF_RULES] == stored


@pytest.mark.parametrize(
    ("rules", "error"),
    [
        pytest.param([_rule("")], "missing_name", id="no_name"),
        pytest.param([_rule("A", source=["Solar"]), _rule("A", source=["Grid"])], "name_exists", id="same_name"),
        pytest.param([_rule("A", source=["Grid"], target=["Grid"])], "source_target_same", id="same_ends"),
        pytest.param(
            [_rule("A", source=["Solar", "Grid"]), _rule("B", source=["Grid", "Solar"])],
            "duplicate_rule",
            id="same_pattern",
        ),
        pytest.param([_rule("A", price=as_none_value())], "required", id="no_price"),
    ],
)
async def test_a_rule_that_cannot_be_saved_is_shown_again_with_the_error(
    hass: HomeAssistant, hub_entry: MockConfigEntry, rules: list[PolicyRuleValue], error: str
) -> None:
    """A problem with any rule keeps the form open on the submitted rules, naming the problem."""
    result = await _create_flow(hass, hub_entry).async_step_user(user_input={CONF_RULES: rules})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == {CONF_RULES: error}
    assert _shown_rules(result) == rules


async def test_the_editor_offers_sources_and_targets_by_role(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Sources are elements that can source power and targets those that can sink it; others are left out."""
    _add_element(hass, hub_entry, "My Load", LOAD_ELEMENT_TYPE)
    _add_element(hass, hub_entry, "My Solar", SOLAR_ELEMENT_TYPE)
    _add_element(hass, hub_entry, "Inverter", INVERTER_ELEMENT_TYPE)
    _add_element(
        hass, hub_entry, "Switchboard", NODE_ELEMENT_TYPE, {SECTION_ROLE: {CONF_IS_SOURCE: False, CONF_IS_SINK: False}}
    )
    _add_element(hass, hub_entry, "Broken", "not-a-real-type")

    config = _selector(await _create_flow(hass, hub_entry).async_step_user(user_input=None)).config

    assert [element["name"] for element in config["sources"]] == ["Solar", "Grid", "Battery", "My Solar"]
    assert [element["name"] for element in config["targets"]] == ["Grid", "Battery", "Load", "My Load"]
    assert config["sources"][3] == {"name": "My Solar", "element_type": SOLAR_ELEMENT_TYPE}


async def test_the_editor_marks_each_rule_an_elements_own_price_stands_for(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Each element's surfaced price fields give the rule pattern they stand for, with the element owning it."""
    _add_element(hass, hub_entry, "Home Battery", BATTERY_ELEMENT_TYPE)

    config = _selector(await _create_flow(hass, hub_entry).async_step_user(user_input=None)).config

    assert config["surfaced"] == [
        {"owner": "Home Battery", "owner_type": BATTERY_ELEMENT_TYPE, "source": None, "target": ["Home Battery"]},
        {"owner": "Home Battery", "owner_type": BATTERY_ELEMENT_TYPE, "source": ["Home Battery"], "target": None},
    ]


async def test_rule_price_offers_compatible_price_entities_and_a_constant(
    hass: HomeAssistant, hub_entry: MockConfigEntry, entity_registry: er.EntityRegistry
) -> None:
    """The price takes entities or a constant, offering price sensors at any energy scale but not HAEO's own."""
    haeo_number = entity_registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="policy_price_constant",
        suggested_object_id="policy_price",
        config_entry=hub_entry,
    )
    hass.states.async_set("sensor.import_price", "0.25", {"unit_of_measurement": "$/kWh"})
    hass.states.async_set("sensor.export_price", "0.05", {"unit_of_measurement": "€/MWh"})
    hass.states.async_set("sensor.power_only", "5", {"unit_of_measurement": "kW"})

    price = _selector(await _create_flow(hass, hub_entry).async_step_user(user_input=None)).config["price"]

    assert price["kinds"] == ["entity", "constant"]
    entities = price.get("entities", [])
    assert {"sensor.import_price", "sensor.export_price"} <= set(entities)
    assert "sensor.power_only" not in entities
    assert haeo_number.entity_id not in entities


def test_extract_policy_rules_includes_disabled_with_enabled_flag() -> None:
    """Disabled rules are included by extract_policy_rules with enabled=False."""
    # The third rule carries an unloaded schema-mode price dict to verify that
    # extract_policy_rules passes prices through untouched.
    config: PolicyConfigData = {
        "element_type": ElementType.POLICY,
        "name": "Policies",
        "rules": [
            {"name": "Active", "source": ["Solar"], "target": ["Grid"], "price": 0.02, "enabled": True},
            {"name": "Disabled", "source": ["Grid"], "target": ["Battery"], "price": 0.05, "enabled": False},
            {
                "name": "Default",
                "enabled": True,
                "source": ["Solar"],
                "target": ["Battery"],
                "price": {"type": "constant", "value": 0.0},  # type: ignore[typeddict-item]
            },
        ],
    }
    result = extract_policy_rules(config)
    assert len(result) == 3
    assert result[0]["sources"] == ["Solar"]
    assert result[0]["destinations"] == ["Grid"]
    assert result[0].get("enabled") is True
    assert result[1]["sources"] == ["Grid"]
    assert result[1]["destinations"] == ["Battery"]
    assert result[1].get("enabled") is False
    assert result[2]["sources"] == ["Solar"]
    assert result[2]["destinations"] == ["Battery"]
    assert result[2].get("enabled") is True

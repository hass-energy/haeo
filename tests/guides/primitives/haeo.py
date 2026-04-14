"""HAEO element primitives for guide automation.

High-level functions that add elements to an HAEO network.
Each function is decorated with @guide_step for automatic screenshot naming.

Field values are typed as EntityInput or ConstantInput to match
the ChooseSelector pattern used in config flows. Parameter names
match the schema field name constants (e.g. CONF_CAPACITY), and
display labels are loaded from translations/en.json at runtime.

This ensures the primitives stay in sync with the actual schemas
and the type system catches mismatches.
"""

from __future__ import annotations

from dataclasses import dataclass
import functools
import json
import logging
from pathlib import Path
import types
from typing import TYPE_CHECKING, Any, get_args

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MIN_CHARGE_PERCENTAGE,
)
from custom_components.haeo.core.schema.elements.element_type import ElementType
from custom_components.haeo.core.schema.sections import (
    CONF_FORECAST,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
)

from .capture import guide_step

if TYPE_CHECKING:
    from custom_components.haeo.elements.input_fields import InputFieldGroups

    from .ha_page import HAPage

_LOGGER = logging.getLogger(__name__)


# region: Field value types


@dataclass(frozen=True, slots=True)
class EntityInput:
    """Entity value for ChooseSelector fields.

    Attributes:
        search_term: Text to search for in the entity picker dialog.
        display_name: Display name of the entity to select from results.

    """

    search_term: str
    display_name: str


@dataclass(frozen=True, slots=True)
class ConstantInput:
    """Constant value for ChooseSelector fields.

    Attributes:
        value: The numeric constant value.

    """

    value: float


type FieldInput = EntityInput | ConstantInput | list[EntityInput]

# endregion


# region: Translation helpers


@functools.cache
def _load_translations() -> dict[str, Any]:
    """Load translations from en.json."""
    path = Path(__file__).parent.parent.parent.parent / "custom_components" / "haeo" / "translations" / "en.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _subentry(element_type: str) -> dict[str, Any]:
    """Get config subentry translations for an element type."""
    return _load_translations()["config_subentries"][element_type]


def _step_user(element_type: str) -> dict[str, Any]:
    """Get the step user translations for an element type."""
    return _subentry(element_type)["step"]["user"]


def _dialog_title(element_type: str) -> str:
    """Get the dialog title for an element type."""
    return _step_user(element_type)["title"]


def _button_label(element_type: str) -> str:
    """Get the button label to initiate an element flow."""
    return _subentry(element_type)["initiate_flow"]["user"]


def _name_label(element_type: str) -> str:
    """Get the display label for the name field."""
    return _step_user(element_type)["data"]["name"]


def _connection_label(element_type: str) -> str:
    """Get the display label for the connection field."""
    return _step_user(element_type)["data"]["connection"]


def _section_name(element_type: str, section_key: str) -> str:
    """Get the display name for a collapsible section."""
    return _step_user(element_type)["sections"][section_key]["name"]


def _field_label(element_type: str, section_key: str, field_name: str) -> str:
    """Get the display label for a field within a section."""
    return _step_user(element_type)["sections"][section_key]["data"][field_name]


# endregion


# region: Schema-driven field filling


def _has_none_value(value_type: Any) -> bool:
    """Check if NoneValue is part of a union type annotation."""
    if isinstance(value_type, types.UnionType):
        from custom_components.haeo.core.schema import NoneValue  # noqa: PLC0415

        return NoneValue in get_args(value_type)
    return False


def _get_default_mode(field_info: Any, value_type: Any) -> str | None:
    """Determine the ChooseSelector's default mode for a field.

    The default mode controls whether a mode switch is needed before
    filling the field. Returns "Entity", "Constant", or None.

    - Fields with explicit default_mode in their FieldHint use that mode.
    - Fields whose type includes NoneValue default to None (no selection).
    - All other fields default to Entity (first available choice).
    """
    if field_info.defaults and field_info.defaults.mode:
        return "Entity" if field_info.defaults.mode == "entity" else "Constant"
    if _has_none_value(value_type):
        return None
    return "Entity"


def _find_section(input_fields: InputFieldGroups, field_name: str) -> str:
    """Find the section key that contains a field."""
    for section_key, fields in input_fields.items():
        if field_name in fields:
            return section_key
    msg = f"Field '{field_name}' not found in input fields"
    raise KeyError(msg)


def _fill_choose_field(
    page: HAPage,
    label: str,
    value: FieldInput,
    default_mode: str | None,
) -> None:
    """Fill a ChooseSelector field based on value type.

    Switches the ChooseSelector mode if needed, then fills the field
    with the appropriate entity or constant value.
    """
    match value:
        case EntityInput():
            if default_mode != "Entity":
                page.choose_select_option(label, "Entity")
            page.choose_entity(label, value.search_term, value.display_name)
        case ConstantInput():
            if default_mode != "Constant":
                page.choose_select_option(label, "Constant")
            page.choose_constant(label, str(value.value))
        case list():
            first = value[0]
            if default_mode != "Entity":
                page.choose_select_option(label, "Entity")
            page.choose_entity(label, first.search_term, first.display_name)
            for entity in value[1:]:
                page.choose_add_entity(label, entity.search_term, entity.display_name)


def _fill_element_fields(
    page: HAPage,
    element_type: ElementType,
    fields: dict[str, FieldInput],
    *,
    collapsed_sections: frozenset[str] = frozenset(),
) -> None:
    """Fill all ChooseSelector fields for an element form.

    Looks up display labels from translations and determines the
    default ChooseSelector mode from the element schema metadata.
    Automatically expands collapsed sections when accessing their fields.

    Fields must be ordered by section (matching the form's top-to-bottom
    layout) to ensure correct section expansion behavior.
    """
    from custom_components.haeo.elements import get_input_field_schema_info, get_input_fields  # noqa: PLC0415

    input_fields = get_input_fields(element_type)
    field_schema = get_input_field_schema_info(element_type, input_fields)
    expanded: set[str] = set()

    for field_name, field_value in fields.items():
        section_key = _find_section(input_fields, field_name)

        # Auto-expand collapsed sections on first field access
        if section_key in collapsed_sections and section_key not in expanded:
            page.expand_section(_section_name(element_type, section_key))
            expanded.add(section_key)

        label = _field_label(element_type, section_key, field_name)
        field_info = input_fields[section_key][field_name]
        value_type = field_schema[section_key][field_name].value_type
        default_mode = _get_default_mode(field_info, value_type)
        _fill_choose_field(page, label, field_value, default_mode)


# endregion


# region: Element primitives


@guide_step
def login(page: HAPage) -> None:
    """Log in to Home Assistant and navigate to integrations."""
    _LOGGER.info("Logging in...")
    page.goto("/")

    if "/auth/authorize" in page.page.url:
        page.fill_textbox("Username", "testuser")
        page.fill_textbox("Password", "testpass")
        page.click_button("Log in")
        page.page.wait_for_url("**/lovelace/**", timeout=5000)

    page.navigate_to_settings()
    page.navigate_to_integrations()

    _LOGGER.info("Logged in")


@guide_step
def add_integration(page: HAPage, *, network_name: str) -> None:
    """Add HAEO integration to Home Assistant."""
    _LOGGER.info("Adding HAEO integration: %s", network_name)

    page.click_add_integration()
    page.search_integration("HAEO")

    page.wait_for_dialog("HAEO Setup")
    page.fill_textbox("System Name", network_name)
    page.submit()

    # Wait for the success dialog before navigating to the integration page.
    # The config entry setup runs inline in the POST handler (HA uses
    # handler_cancellation=True), so navigating before the response
    # arrives cancels the setup task.
    page.close_success_dialog()

    page.navigate_to_integration("HAEO")

    _LOGGER.info("HAEO integration added")


@guide_step
def add_inverter(
    page: HAPage,
    *,
    name: str,
    connection: str,
    max_power_source_target: EntityInput,
    max_power_target_source: EntityInput,
) -> None:
    """Add inverter element to HAEO network."""
    et = ElementType.INVERTER
    _LOGGER.info("Adding Inverter: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)
    page.select_combobox(_connection_label(et), connection)

    _fill_element_fields(
        page,
        et,
        {
            CONF_MAX_POWER_SOURCE_TARGET: max_power_source_target,
            CONF_MAX_POWER_TARGET_SOURCE: max_power_target_source,
        },
    )

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Inverter added: %s", name)


@guide_step
def add_battery(
    page: HAPage,
    *,
    name: str,
    connection: str,
    capacity: EntityInput,
    initial_charge_percentage: EntityInput,
    max_power_target_source: EntityInput | None = None,
    max_power_source_target: EntityInput | None = None,
    min_charge_percentage: EntityInput | ConstantInput | None = None,
    max_charge_percentage: EntityInput | ConstantInput | None = None,
) -> None:
    """Add battery element to HAEO network."""
    et = ElementType.BATTERY
    _LOGGER.info("Adding Battery: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)
    page.select_combobox(_connection_label(et), connection)

    # Build fields dict in section order: storage → limits → power_limits
    fields: dict[str, FieldInput] = {
        CONF_CAPACITY: capacity,
        CONF_INITIAL_CHARGE_PERCENTAGE: initial_charge_percentage,
    }
    if min_charge_percentage is not None:
        fields[CONF_MIN_CHARGE_PERCENTAGE] = min_charge_percentage
    if max_charge_percentage is not None:
        fields[CONF_MAX_CHARGE_PERCENTAGE] = max_charge_percentage
    if max_power_target_source is not None:
        fields[CONF_MAX_POWER_TARGET_SOURCE] = max_power_target_source
    if max_power_source_target is not None:
        fields[CONF_MAX_POWER_SOURCE_TARGET] = max_power_source_target

    _fill_element_fields(
        page,
        et,
        fields,
        collapsed_sections=frozenset({"efficiency", "partitioning"}),
    )

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Battery added: %s", name)


@guide_step
def add_solar(
    page: HAPage,
    *,
    name: str,
    connection: str,
    forecast: EntityInput | list[EntityInput],
) -> None:
    """Add solar element to HAEO network."""
    et = ElementType.SOLAR
    _LOGGER.info("Adding Solar: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)
    page.select_combobox(_connection_label(et), connection)

    _fill_element_fields(
        page,
        et,
        {CONF_FORECAST: forecast},
        collapsed_sections=frozenset({"curtailment"}),
    )

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Solar added: %s", name)


@guide_step
def add_grid(
    page: HAPage,
    *,
    name: str,
    connection: str,
    price_source_target: EntityInput | list[EntityInput],
    price_target_source: EntityInput | list[EntityInput],
    max_power_source_target: ConstantInput | None = None,
    max_power_target_source: ConstantInput | None = None,
) -> None:
    """Add grid element to HAEO network."""
    et = ElementType.GRID
    _LOGGER.info("Adding Grid: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)
    page.select_combobox(_connection_label(et), connection)

    # Build fields dict in section order: pricing → power_limits
    fields: dict[str, FieldInput] = {
        CONF_PRICE_SOURCE_TARGET: price_source_target,
        CONF_PRICE_TARGET_SOURCE: price_target_source,
    }
    if max_power_source_target is not None:
        fields[CONF_MAX_POWER_SOURCE_TARGET] = max_power_source_target
    if max_power_target_source is not None:
        fields[CONF_MAX_POWER_TARGET_SOURCE] = max_power_target_source

    _fill_element_fields(
        page,
        et,
        fields,
        collapsed_sections=frozenset({"power_limits"}),
    )

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Grid added: %s", name)


@guide_step
def add_load(
    page: HAPage,
    *,
    name: str,
    connection: str,
    forecast: EntityInput | ConstantInput,
) -> None:
    """Add load element to HAEO network."""
    et = ElementType.LOAD
    _LOGGER.info("Adding Load: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)
    page.select_combobox(_connection_label(et), connection)

    _fill_element_fields(
        page,
        et,
        {CONF_FORECAST: forecast},
        collapsed_sections=frozenset({"pricing", "curtailment"}),
    )

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Load added: %s", name)


@guide_step
def add_node(page: HAPage, *, name: str) -> None:
    """Add node element to HAEO network."""
    et = ElementType.NODE
    _LOGGER.info("Adding Node: %s", name)

    page.click_button(_button_label(et))
    page.wait_for_dialog(_dialog_title(et))

    page.fill_textbox(_name_label(et), name)

    page.submit()
    page.close_element_dialog()

    _LOGGER.info("Node added: %s", name)


@guide_step
def verify_setup(page: HAPage) -> None:
    """Verify the HAEO setup is complete."""
    _LOGGER.info("Verifying setup...")

    page._capture("final_overview")

    _LOGGER.info("Setup verified")


@guide_step
def add_policies(
    page: HAPage,
    *,
    name: str,
    source: str | list[str] | None = None,
    target: str | list[str] | None = None,
    price: float | None = None,
) -> None:
    """Add a policy rule via the Policies subentry flow.

    Works for both the first rule (creates subentry) and subsequent
    rules (appends to existing subentry).

    Source and target use a ChooseSelector with Any/Nodes choices.
    When nodes are specified, the nested dropdown multi-select is used.
    Pass a string for a single node, a list for multiple nodes, or None for "Any".
    Price uses a ChooseSelector with Constant/Entity/None choices.
    """
    et = "policy"
    _LOGGER.info("Adding policy rule: %s", name)

    page.click_button(_button_label(et), first=True)
    page.wait_for_dialog(_dialog_title(et))

    step_data = _step_user(et)["data"]
    page.fill_textbox(step_data["name"], name)

    if source is not None:
        nodes = [source] if isinstance(source, str) else source
        page.choose_select_option(step_data["source"], "Nodes")
        page.choose_dropdown_multi(step_data["source"], nodes)
    if target is not None:
        nodes = [target] if isinstance(target, str) else target
        page.choose_select_option(step_data["target"], "Nodes")
        page.choose_dropdown_multi(step_data["target"], nodes)
    if price is not None:
        page.choose_select_option(step_data["price"], "Constant")
        page.choose_constant(step_data["price"], str(price))

    page.submit()

    # First add: async_create_entry shows a Finish dialog.
    # Subsequent adds: async_update_and_abort shows an abort dialog
    # with a close button in the header (Escape/scrim are disabled).
    finish = page.page.get_by_role("button", name="Finish")
    try:
        finish.wait_for(state="visible", timeout=2000)
    except PlaywrightTimeoutError:
        # Close the abort dialog via the header X button
        close_btn = page.page.locator(
            "dialog-data-entry-flow ha-icon-button[dialogaction='close']",
        )
        close_btn.click(timeout=2000)
        page.page.locator("dialog-data-entry-flow ha-dialog[open]").wait_for(
            state="detached",
            timeout=5000,
        )
        _LOGGER.info("Policy appended to existing subentry")
    else:
        page.close_element_dialog()

    _LOGGER.info("Policy rule added: %s", name)


@guide_step
def reconfigure_policies(page: HAPage) -> None:
    """Open the reconfigure flow for the Policies subentry.

    Scrolls to and clicks the gear icon on the Policies subentry row.
    """
    _LOGGER.info("Opening policy reconfigure...")

    et = "policy"
    policies_row = page.page.locator("ha-md-list-item.sub-entry").filter(has_text="Policies")
    policies_row.wait_for(state="visible", timeout=5000)
    policies_row.scroll_into_view_if_needed()

    # The first ha-icon-button in a subentry row is the expand/collapse chevron
    # (class="expand-button", slot="start"). The gear button comes after it.
    gear_button = policies_row.locator("ha-icon-button:not([slot='start'])").first
    page._capture("reconfigure_gear")
    gear_button.click(timeout=2000)

    page.wait_for_dialog(_step_title(et, "reconfigure"))

    _LOGGER.info("Policy reconfigure opened")


def _step_title(element_type: str, step: str) -> str:
    """Get the title for a specific flow step."""
    return _subentry(element_type)["step"][step]["title"]


# endregion

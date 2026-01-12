"""Tests for grid element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.elements import node
from custom_components.haeo.elements.grid import CONF_CONNECTION, CONF_EXPORT_PRICE, CONF_IMPORT_PRICE, ELEMENT_TYPE

from tests.conftest import TEST_CONFIGURABLE_ENTITY_ID

from ..conftest import add_participant, create_flow


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Grid reconfigure should include deleted connection target in options."""
    # Create grid that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
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

    # Show reconfigure form - should not error
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_get_participant_names_skips_unknown_element_types(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    # Add a valid participant
    add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    # Add a subentry with unknown element type
    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Get participant names - should only include ValidNode
    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_current_subentry_id_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_current_subentry_id should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry_id = flow._get_current_subentry_id()

    assert subentry_id is None


# --- Tests for validation errors ---


async def test_user_step_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting step 1 with empty required field should show required error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit with empty import_price (required field)
    user_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=user_input)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


# --- Tests for two-step flow with configurable values ---


async def test_user_step_with_configurable_shows_values_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting configurable entity should show values form (step 2)."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Submit step 1 with configurable entities selected
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)

    # Should show values form (step 2)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"


async def test_values_step_creates_entry_with_constant(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting values step should create entry with constant values."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Grid",
            "data": {},
        }
    )

    # Step 1: select configurable entities
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: provide constant values
    step2_input = {
        CONF_IMPORT_PRICE: 0.25,
        CONF_EXPORT_PRICE: 0.05,
    }
    result = await flow.async_step_values(user_input=step2_input)

    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the config contains the constant values
    create_kwargs = flow.async_create_entry.call_args.kwargs
    assert create_kwargs["data"][CONF_IMPORT_PRICE] == 0.25
    assert create_kwargs["data"][CONF_EXPORT_PRICE] == 0.05


async def test_values_step_missing_required_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting values step with missing required configurable value should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Step 1: select configurable entities
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_user(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: submit without providing import_price (required configurable value)
    step2_input = {
        CONF_EXPORT_PRICE: 0.05,
    }
    result = await flow.async_step_values(user_input=step2_input)

    # Should show values form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


# --- Tests for reconfigure flow ---


async def test_reconfigure_empty_required_field_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with empty required field should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
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

    # Submit with empty import_price (required field)
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should show reconfigure form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


async def test_reconfigure_with_configurable_shows_values_form(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with configurable entity should show values form."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
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

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should show values form (step 2)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"


async def test_reconfigure_values_step_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Submitting reconfigure values step should update entry."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
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

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: provide constant values
    step2_input = {
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.08,
    }
    result = await flow.async_step_values(user_input=step2_input)

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config contains the constant values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_IMPORT_PRICE] == 0.30
    assert update_kwargs["data"][CONF_EXPORT_PRICE] == 0.08


async def test_reconfigure_values_step_missing_required_shows_error(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure values step with missing required configurable value should show error."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with sensor links
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: ["sensor.import"],
        CONF_EXPORT_PRICE: ["sensor.export"],
    }
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

    # Step 1: change to configurable entities
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Step 2: submit without providing import_price (required configurable value)
    step2_input = {
        CONF_EXPORT_PRICE: 0.08,
    }
    result = await flow.async_step_values(user_input=step2_input)

    # Should show reconfigure_values form again with error
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"
    assert CONF_IMPORT_PRICE in result.get("errors", {})


async def test_reconfigure_with_scalar_shows_resolved_entity(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with scalar values should show resolved HAEO entity in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values (from prior configurable entity setup)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,  # Scalar value, not entity link
        CONF_EXPORT_PRICE: 0.08,  # Scalar value, not entity link
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    # Register HAEO number entities in entity registry (simulating what number.py does)
    registry = er.async_get(hass)
    import_price_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_IMPORT_PRICE}",
        suggested_object_id="test_grid_import_price",
    )
    export_price_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_EXPORT_PRICE}",
        suggested_object_id="test_grid_export_price",
    )

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Find the suggested values for import_price and export_price
    # The schema keys are vol.Required/Optional markers, values are selectors
    # We need to check what _build_step1_defaults returned
    defaults = flow._build_step1_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain the resolved entity IDs
    assert defaults[CONF_IMPORT_PRICE] == [import_price_entity.entity_id]
    assert defaults[CONF_EXPORT_PRICE] == [export_price_entity.entity_id]
    # Should NOT be the configurable sentinel
    assert defaults[CONF_IMPORT_PRICE] != [TEST_CONFIGURABLE_ENTITY_ID]
    assert defaults[CONF_EXPORT_PRICE] != [TEST_CONFIGURABLE_ENTITY_ID]


async def test_reconfigure_with_scalar_selecting_configurable_triggers_step2(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Selecting configurable entity during reconfigure should trigger step 2."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.08,
    }
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

    # User selects configurable entity to change the value
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],  # Want to change this
        CONF_EXPORT_PRICE: [TEST_CONFIGURABLE_ENTITY_ID],  # Want to change this
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should show values form (step 2) to enter new values
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"


async def test_reconfigure_with_string_entity_id_v010_format(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfigure with v0.1.0 string entity ID should show entity in defaults."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with v0.1.0 format: string entity IDs (not list, not scalar)
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: "sensor.import_price",  # v0.1.0: single string entity ID
        CONF_EXPORT_PRICE: "sensor.export_price",  # v0.1.0: single string entity ID
    }
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

    # Show reconfigure form (user_input=None)
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    # Check defaults - should have the string entity IDs wrapped in lists
    defaults = flow._build_step1_defaults("Test Grid", dict(existing_subentry.data))

    # Defaults should contain the original entity IDs as lists
    assert defaults[CONF_IMPORT_PRICE] == ["sensor.import_price"]
    assert defaults[CONF_EXPORT_PRICE] == ["sensor.export_price"]


async def test_reconfigure_keeping_resolved_entity_preserves_scalar(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Keeping resolved entity selected should preserve original scalar value."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    # Create existing entry with scalar values
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: 0.30,
        CONF_EXPORT_PRICE: 0.08,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Grid",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    # Register HAEO number entities in entity registry
    registry = er.async_get(hass)
    import_price_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_IMPORT_PRICE}",
        suggested_object_id="test_grid_import_price",
    )
    export_price_entity = registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id=f"{hub_entry.entry_id}_{existing_subentry.subentry_id}_{CONF_EXPORT_PRICE}",
        suggested_object_id="test_grid_export_price",
    )

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # User keeps the resolved entities selected (no change)
    step1_input = {
        CONF_NAME: "Test Grid",
        CONF_CONNECTION: "TestNode",
        CONF_IMPORT_PRICE: [import_price_entity.entity_id],  # Keep resolved entity
        CONF_EXPORT_PRICE: [export_price_entity.entity_id],  # Keep resolved entity
    }
    result = await flow.async_step_reconfigure(user_input=step1_input)

    # Should skip step 2 and complete (no configurable entity selected)
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the config preserves the original scalar values
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["data"][CONF_IMPORT_PRICE] == 0.30  # Original scalar preserved
    assert update_kwargs["data"][CONF_EXPORT_PRICE] == 0.08  # Original scalar preserved

---
name: config-flow
description: Config flow and subentry flow development — the hub flow and options flow in flows/hub.py and flows/options.py, element subentry flows in flows/elements/ built on ElementSubentryFlow and ConnectedElementSubentryFlow, form sections in flows/sections/, schema generation from field hints, validation timing, unique IDs, and flow errors. Use when working under flows/ or config_flow.py, or when changing how the hub or elements are configured in the Home Assistant UI.
---

# Config flow development

HAEO uses Home Assistant's ConfigSubentry architecture for element management.
See [config flow documentation](../../../docs/developer-guide/config-flow.md) for detailed patterns.

## Subentry flow pattern

`HubConfigFlow.async_get_supported_subentry_types()` offers one subentry flow per element type, from the map `get_element_flow_classes()` in `flows/__init__.py` returns.
Types whose adapter sets `advanced` are offered only when the hub has advanced mode on.

Every element flow subclasses `ElementSubentryFlow` in [`flows/element_flow.py`](../../../custom_components/haeo/flows/element_flow.py).
It provides name validation, the participants an element can connect to, the on/off states step, and the save path.
A flow declares its type with the `element_type` class attribute.

Every flow also declares a `sections` class attribute.
A flow whose form is sections of choose inputs subclasses `SectionedElementSubentryFlow` in [`flows/sectioned_flow.py`](../../../custom_components/haeo/flows/sectioned_flow.py), which builds the form, defaults, validation, saving, and surfaced policy pricing fields from `element_type` and `sections`.
It adds fields outside the sections by overriding the hooks `_top_level_entries`, `_top_level_defaults`, `_section_entries`, `_section_defaults`, `_validate_fields`, and `_config_fields`, rather than writing steps.
An element that connects to one other element subclasses `ConnectedElementSubentryFlow` in [`flows/connected_flow.py`](../../../custom_components/haeo/flows/connected_flow.py), which implements those hooks for `connection`.
Write custom steps only for an element whose form does not fit that shape.
A surfaced policy price field shows only if one of the flow's `sections` lists it.

Build `sections` from the helpers in `flows/sections/`.
Each element type's schema class defines the fields via TypedDict + Annotated + field hints (`FieldHint`, `SectionHints`, `ListFieldHints`), which drive the form, its defaults, and how each value loads.
Do not hand-maintain defaults in a flow.

When modifying config flows, changes to the flow or schema may require corresponding updates to `docs/developer-guide/config-flow.md`.

## Version control

The hub flow sets `VERSION` and `MINOR_VERSION`.
`MINOR_VERSION` is `MIGRATION_MINOR_VERSION` from `migrations/`, so adding a migration bumps it.

## Unique ID management

Prevent duplicate entries using unique IDs or data matching:

```python
await self.async_set_unique_id(device_unique_id)
self._abort_if_unique_id_configured()

# Or using data matching
self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
```

## Data storage

- Hub settings live in sections of `ConfigEntry.data`.
    The options flow writes its changes back to `data` with `async_update_entry` and leaves `options` empty.
- Element settings live in the subentry's `data`, in the shape its `{Type}ConfigSchema` declares.

## Naming

Users can name their config entries and elements.
Element names must be unique within a hub and are validated during the flow.
An element form keeps its `name` and `connection` fields at the top level of the form, outside any section.

## Validation timing

Validate naming, required fields, endpoints, and schema constraints in the flow.
Do not load input entities or run network connectivity checks during configuration.
Connectivity validation runs in the coordinator after input entities are loaded.
Repair issues are created from the coordinator based on loaded configurations.

## Error handling

Set errors on the form's `errors` dict, keyed by field or `base`, and translate each in `en.json` under the flow that shows it:

- Hub flow: `config.error`
- Options flow: `options.error`
- Element subentry flow: `config_subentries.{type}.error`

Key an error for a field inside a form section by the section instead, because Home Assistant only shows errors for top-level form fields and otherwise re-shows the form without saying why.

The runtime translation checker fails a test that shows an error key `en.json` lacks; see the `translations` skill.

## Step naming

Use standard step names:

- `async_step_user` - User-initiated flow (new element creation)
- `async_step_reconfigure` - Reconfiguration of an existing element, or of the hub, whose reconfigure step shares the options flow's schema

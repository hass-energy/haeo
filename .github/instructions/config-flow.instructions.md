---
applyTo: '**/config_flow.py,**/flows/**'
description: Config flow development standards
globs: ['**/config_flow.py', '**/flows/**']
alwaysApply: false
---

# Config flow development

HAEO uses Home Assistant's ConfigSubentry architecture for element management.
See [config flow documentation](../../docs/developer-guide/config-flow.md) for detailed patterns.

## Subentry flow pattern

Element flows are created dynamically from the `ELEMENT_TYPES` registry using `create_subentry_flow_class()`.
Each element type's schema class defines the form fields via TypedDict + Annotated + composable metadata (Validator, LoaderMeta, Default).

When modifying config flows, changes to the flow or schema may require corresponding updates to `docs/developer-guide/config-flow.md`.

## Version control

Always set version numbers on config flows:

```python
class ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1
```

## Unique ID management

Prevent duplicate entries using unique IDs or data matching:

```python
await self.async_set_unique_id(device_unique_id)
self._abort_if_unique_id_configured()

# Or using data matching
self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
```

## Data storage

- Connection-critical config → `ConfigEntry.data`
- User-editable settings → `ConfigEntry.options`

## Naming

Users can name their config entries and elements.
Element names must be unique within a hub and are validated during the flow.

## Data loading validation

Validate that entity references work during the config flow.
The `evaluate_network_connectivity()` function tests that configured sensors can be loaded:

```python
participant_configs[new_config[CONF_NAME]] = new_config
await evaluate_network_connectivity(self.hass, hub_entry, participant_configs=participant_configs)
```

This ensures entity IDs are valid and loaders can extract data before saving the configuration.

## Error handling

Define errors in translation files under `config.error`.
HAEO uses `en.json` (not `strings.json`) as a custom integration:

```json
{
  "config": {
    "error": {
      "cannot_connect": "Failed to connect",
      "name_exists": "An element with this name already exists"
    }
  }
}
```

## Step naming

Use standard step names:

- `async_step_user` - User-initiated flow (new element creation)
- `async_step_reconfigure` - Reconfiguration of existing element

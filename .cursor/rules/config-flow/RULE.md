---
description: Config flow development patterns
globs: ['**/config_flow.py', '**/flows/**']
alwaysApply: false
---

# Config flow development

## Version control

Always set version numbers:

```python
class ConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1
```

## Unique ID management

Prevent duplicate entries:

```python
await self.async_set_unique_id(device_unique_id)
self._abort_if_unique_id_configured()

# Or using data matching
self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
```

## Data storage

- Connection-critical config → `ConfigEntry.data`
- Non-critical settings → `ConfigEntry.options`

## Naming rules

- ❌ Do NOT allow users to set config entry names in config flows
- Names are automatically generated or customized later in UI

## Polling rules

- ❌ Do NOT allow user-configurable polling intervals
- Integration determines intervals programmatically

## Connection testing

Always test connection during config flow:

```python
try:
    await client.get_data()
except MyException:
    errors["base"] = "cannot_connect"
```

## Error handling

Define errors in `strings.json` under `config.error`:

```json
{
  "config": {
    "error": {
      "cannot_connect": "Failed to connect",
      "invalid_auth": "Invalid authentication"
    }
  }
}
```

## Reauthentication

Implement `async_step_reauth` for credential updates:

```python
async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
    """Handle reauthentication."""
    return await self.async_step_reauth_confirm()


async def async_step_reauth_confirm(self, user_input=None) -> ConfigFlowResult:
    if user_input:
        # Verify new credentials match same account
        await self.async_set_unique_id(user_id)
        self._abort_if_unique_id_mismatch(reason="wrong_account")
        return self.async_update_reload_and_abort(
            self._get_reauth_entry(), data_updates={CONF_API_TOKEN: user_input[CONF_API_TOKEN]}
        )
    return self.async_show_form(step_id="reauth_confirm", data_schema=SCHEMA)
```

## Reconfiguration

Implement `async_step_reconfigure` for config updates without removal:

```python
async def async_step_reconfigure(self, user_input=None) -> ConfigFlowResult:
    """Handle reconfiguration."""
    # Prevent changing underlying account
    self._abort_if_unique_id_mismatch()
    ...
```

## Step naming

Use standard step names:

- `async_step_user` - User-initiated flow
- `async_step_reauth` - Reauthentication
- `async_step_reconfigure` - Reconfiguration

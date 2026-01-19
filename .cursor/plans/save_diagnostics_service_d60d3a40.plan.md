---
name: Save Diagnostics Service
overview: Add a new Home Assistant service `haeo.save_diagnostics` that saves a diagnostics file to the config directory, reusing the existing diagnostics generation logic. The service will include a dropdown selector for choosing which HAEO hub to target.
todos:
  - id: create-services-yaml
    content: Create services.yaml with save_diagnostics service definition
    status: completed
  - id: add-async-setup
    content: Add async_setup function to register the service in __init__.py
    status: completed
  - id: add-translations
    content: Add service translations to en.json
    status: completed
  - id: add-tests
    content: Add tests for the new service
    status: completed
---

# Add `haeo.save_diagnostics` Service

## Overview

Create a new service action that saves diagnostics to the config directory, leveraging the existing `async_get_config_entry_diagnostics` function. The service will use a `config_entry` selector to provide a dropdown of HAEO hubs.

## Files to Create/Modify

### 1. Create `services.yaml`

Create [`custom_components/haeo/services.yaml`](custom_components/haeo/services.yaml) to define the service schema:

```yaml
save_diagnostics:
  fields:
    config_entry:
      required: true
      selector:
        config_entry:
          integration: haeo
```

The `config_entry` selector with `integration: haeo` filter will automatically show a dropdown of all configured HAEO hubs.

### 2. Modify `__init__.py`

Add an `async_setup` function to [`custom_components/haeo/__init__.py`](custom_components/haeo/__init__.py) to register the service. This must be done in `async_setup` (not `async_setup_entry`) so the service is available even when no entries are loaded.

The service handler will:

- Validate the config entry exists and is loaded
- Call the existing `async_get_config_entry_diagnostics` function
- Write the JSON to `<config_dir>/haeo_diagnostics_<entry_id>_<timestamp>.json`
- Use `HomeAssistantError` with translation keys for error handling

### 3. Update translations

Add service translations to [`custom_components/haeo/translations/en.json`](custom_components/haeo/translations/en.json):

```json
{
  "services": {
    "save_diagnostics": {
      "name": "Save diagnostics",
      "description": "Save a diagnostics file for a HAEO hub to the config directory",
      "fields": {
        "config_entry": {
          "name": "Hub",
          "description": "The HAEO hub to save diagnostics for"
        }
      }
    }
  }
}
```

## Implementation Details

- **File naming**: `haeo_diagnostics_<entry_id>_<timestamp>.json` where timestamp is ISO format
- **File location**: Directly in the config directory (same level as `configuration.yaml`)
- **Error handling**: Use `ServiceValidationError` for invalid input, `HomeAssistantError` for runtime errors
- **Async file I/O**: Use `hass.async_add_executor_job` for file writing to avoid blocking the event loop

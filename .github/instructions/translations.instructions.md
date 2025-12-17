---
applyTo: '**/translations/**,**/strings.json'
---

# Translation and user-facing text

## Writing style

- **Tone**: Friendly and informative
- **Perspective**: Second person ("you" and "your")
- **Clarity**: Write for non-native English speakers
- **Case**: Sentence case for all titles and messages
- **Abbreviations**: Avoid when possible

## Formatting in messages

- Use backticks for: file paths, filenames, variable names, field entries
- Example: "Check the `config.json` file"

## strings.json structure

```json
{
  "config": {
    "step": {
      "user": {
        "title": "Configure HAEO",
        "description": "Set up your energy network",
        "data": {
          "name": "Network name"
        }
      }
    },
    "error": {
      "cannot_connect": "Failed to connect to the device",
      "invalid_auth": "Invalid authentication credentials"
    },
    "abort": {
      "already_configured": "This device is already configured"
    }
  },
  "entity": {
    "sensor": {
      "battery_power": {
        "name": "Battery power"
      },
      "grid_import": {
        "name": "Grid import"
      }
    }
  },
  "exceptions": {
    "invalid_config": {
      "message": "The configuration is invalid: {reason}"
    }
  },
  "issues": {
    "outdated_version": {
      "title": "Firmware update required",
      "description": "Your device firmware is outdated. To update: 1) Open the app, 2) Go to settings, 3) Select update."
    }
  }
}
```

## Repair issues

All repair issues must be actionable:

- Clearly explain what is happening
- Provide specific steps to resolve (numbered list)
- Include relevant context (device names, error details)
- Explain what to expect after following the steps

❌ Bad: "Update firmware"
✅ Good: "Your device firmware version \{version} is outdated. To update: 1) Open the manufacturer's app, 2) Navigate to device settings, 3) Select 'Update Firmware'."

## Entity translations

Use translation keys for entity names:

```python
class MySensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "battery_power"
```

## Exception translations

Use translation keys for user-facing exceptions:

```python
raise ServiceValidationError(
    translation_domain=DOMAIN,
    translation_key="invalid_config",
    translation_placeholders={"reason": "missing battery"},
)
```

## Icon translations

Support dynamic icons based on state:

```json
{
  "entity": {
    "sensor": {
      "battery_level": {
        "default": "mdi:battery",
        "state": {
          "low": "mdi:battery-low",
          "charging": "mdi:battery-charging"
        }
      }
    }
  }
}
```

## Sensor naming conventions

HAEO uses consistent patterns for sensor translation display names.
These patterns affect both the UI display and the generated entity IDs.

### Translation key patterns (entity_id generation)

Translation keys use subject-first ordering with underscores:

- `power_import`, `power_export`, `power_charge`, `power_discharge`
- `power_max_import`, `state_of_charge`
- Element prefix pattern: `{element}_{property}_{qualifier}` (e.g., `battery_power_charge`, `grid_price_import`)

### Display name patterns (UI strings)

Display names follow these patterns for consistency, using sentence case (capital first letter, rest lowercase):

1. **Power sensors**: Action + noun pattern

    - ✓ Correct: "Import power", "Export power", "Charge power", "Discharge power", "Active power"
    - ✗ Incorrect: "Power import", "Power export", "Power charge", "Power active"
    - Qualified variants: "\{Qualifier} \{action} power" (e.g., "Normal charge power", "Max import power")

2. **Price sensors**: Qualifier + price pattern

    - ✓ Correct: "Import price", "Export price", "Production price"
    - ✗ Incorrect: "Price (Import)", "Price import"

3. **Shadow price sensors**: Constraint description + "shadow price"

    - ✓ Correct: "Max import power shadow price", "Power balance shadow price", "SOC max shadow price"
    - ✗ Incorrect: "Max Import Price (Shadow)", "Shadow Price (Max Import)"
    - Pattern emphasizes "shadow price" as the subject being described

4. **State/status sensors**: Noun phrase

    - "State of charge", "Energy stored", "Optimization status"

### Avoid special characters

Do not use parentheses, brackets, or other special characters in display names.
These characters can interfere with entity ID generation and cause issues.

❌ Bad: "Power (Source to Target)", "Max Import Price (Shadow)"
✅ Good: "\{source} to \{target} power", "Max import power shadow price"

### Connection sensor parameterized translations

Connection sensors use `{source}` and `{target}` placeholders to display actual element names:

```json
{
  "entity": {
    "sensor": {
      "connection_power_source_target": {
        "name": "{source} to {target} power"
      },
      "connection_power_target_source": {
        "name": "{target} to {source} power"
      },
      "connection_shadow_power_max_source_target": {
        "name": "Max {source} to {target} power shadow price"
      }
    }
  }
}
```

The sensor class must set `_attr_translation_placeholders` with the subentry configuration data.
All subentry.data fields are passed as placeholders (converted to strings), making any configuration value available for use in translations:

```python
# In sensors/__init__.py - all subentry.data fields become available as placeholders
translation_placeholders = {k: str(v) for k, v in subentry.data.items()}

# For connections, this includes: source, target, max_power_source_target, etc.
# For batteries: capacity, efficiency, min_charge_percentage, etc.
# For grids: import_limit, export_limit, import_price, etc.
```

The HaeoSensor class accepts these placeholders:

```python
class HaeoSensor(SensorEntity):
    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        translation_placeholders: dict[str, str] | None = None,
    ):
        if translation_placeholders is not None:
            self._attr_translation_placeholders = translation_placeholders
```

## Home Assistant entity naming requirements

HAEO follows Home Assistant's entity naming conventions:

### Required properties

- `has_entity_name = True` - Required for all new integrations
- `translation_key` - Used to look up translated entity names
- `translation_placeholders` - Optional dict for parameterized translations

### Entity name composition

Home Assistant generates `friendly_name` by combining device and entity names:

- Entity not in device: `friendly_name = entity.name`
- Entity in device with name: `friendly_name = f"{device.name} {entity.name}"`
- Entity in device with `name=None`: `friendly_name = device.name`

### Capitalization

Entity names should start with a capital letter, rest lowercase (unless proper noun or abbreviation):

- ✓ Correct: "Import power", "State of charge", "SOC max shadow price"
- ✗ Incorrect: "Import Power", "STATE OF CHARGE"

### Documentation references

- [Entity naming](https://developers.home-assistant.io/docs/core/entity/#entity-naming)
- [Backend localization](https://developers.home-assistant.io/docs/internationalization/core)
- [Custom integration localization](https://developers.home-assistant.io/docs/internationalization/custom_integration)

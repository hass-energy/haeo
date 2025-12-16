---
description: "Translation and user-facing text standards"
globs: ["**/translations/**", "**/strings.json"]
alwaysApply: false
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
✅ Good: "Your device firmware version {version} is outdated. To update: 1) Open the manufacturer's app, 2) Navigate to device settings, 3) Select 'Update Firmware'."

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

---
name: translations
description: User-facing strings in translations/en.json — sensor and device display names and their naming patterns, entity translation keys and placeholders, config flow labels and errors, exception and repair issue messages, and the translation tests that require every used key and no unused ones. Use when adding, renaming, or removing any user-visible string, entity name, or output sensor, or when a translation test fails.
---

# Translation and user-facing text

HAEO uses `translations/en.json` as a custom integration (not `strings.json` like core integrations).

## Writing style

- **Tone**: Friendly and informative
- **Perspective**: Second person ("you" and "your")
- **Clarity**: Write for non-native English speakers
- **Case**: Sentence case for all titles and messages
- **Abbreviations**: Avoid when possible

## Formatting in messages

- Use backticks for: file paths, filenames, variable names, field entries
- Example: "Check the `config.json` file"

## en.json structure

The top-level groups are `config` (hub flow), `options` (hub options flow), `config_subentries` (one group per element type and the network), `device`, `entity`, `exceptions`, `issues`, `selector`, `services`, and `common` (strings HAEO reads itself).
Read an existing entry in [`en.json`](../../../custom_components/haeo/translations/en.json) for the shape of each, for example:

```json
{
  "config_subentries": {
    "grid": {
      "step": {
        "user": {
          "title": "Grid configuration",
          "data": {
            "connection": "Connection",
            "name": "Grid name"
          },
          "sections": {
            "pricing": {
              "name": "Pricing",
              "data": {
                "price_source_target": "Import price",
                "price_target_source": "Export price"
              }
            }
          }
        }
      },
      "error": {
        "name_exists": "A device with this name already exists"
      }
    }
  },
  "exceptions": {
    "inputs_not_aligned": {
      "message": "The forecast inputs are still loading for the new planning horizon. Try again in a moment."
    }
  }
}
```

An element flow's `name` and `connection` labels sit in the step's top-level `data`, because those fields are outside every section.
Labels for sectioned fields sit under `sections.{section}.data`.

## Checking translations

These checks keep `en.json` and the code in step, and all fail CI:

- `test_translations_match_used_keys` in `translations/tests/test_translations.py` requires every key the integration uses to be present, and every key present to be used.
    Delete a string in the same change that stops using it.

- The pytest plugin [`translations/tests/runtime_checks.py`](../../../custom_components/haeo/translations/tests/runtime_checks.py) runs in every test.
    It fails a test that shows a flow form, abort, repair issue, translated error, entity name, or enum state whose string or placeholder `en.json` lacks.

- [`translations/tests/flow_messages.py`](../../../custom_components/haeo/translations/tests/flow_messages.py) reads each flow's code to find the errors, aborts, and steps its `async_step_*` methods can reach, so the translation tests require strings for exactly those.

So tests must use real translation keys, never placeholders such as `"test_error"`.

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
    _attr_translation_key = "battery_power_charge"
```

Output sensors use the output name as their translation key.
Input entities use `{element_type}_{field_name}`, which `elements/field_hints.py` builds from the schema.

## Exception translations

Use translation keys for user-facing exceptions:

```python
raise HomeAssistantError(
    translation_domain=DOMAIN,
    translation_key="input_unavailable",
    translation_placeholders={"field": field, "element": element, "entities": entities},
)
```

## Icons

Icons live in `icons.json`, not `en.json`.

## Sensor naming conventions

HAEO uses consistent patterns for sensor translation display names.
These patterns affect both the UI display and the generated entity IDs.

### Translation key patterns (entity_id generation)

Output names, and so translation keys, use subject-first ordering with an element prefix: `{element}_{property}_{qualifier}`, such as `battery_power_charge`, `grid_power_import`, and `battery_state_of_charge`.

### Display name patterns (UI strings)

Display names follow these patterns for consistency, using sentence case (capital first letter, rest lowercase):

1. **Power sensors**: Action + noun pattern

    - ✓ Correct: "Import power", "Export power", "Charge power", "Discharge power", "Active power"
    - ✗ Incorrect: "Power import", "Power export", "Power charge", "Power active"
    - Qualified variants: "\{Qualifier} \{action} power" (e.g., "Max charge power", "Max discharge power")

2. **Price entities**: Qualifier + price pattern

    - ✓ Correct: "Import price", "Export price", "Shortfall price"
    - ✗ Incorrect: "Price (Import)", "Price import"

3. **Shadow price sensors**: Constraint description + "shadow price"

    - ✓ Correct: "Max import power shadow price", "Power balance shadow price", "SOC max shadow price"
    - ✗ Incorrect: "Max Import Price (Shadow)", "Shadow Price (Max Import)"
    - Pattern emphasizes "shadow price" as the subject being described

4. **State/status sensors**: Noun phrase

    - "State of charge", "Energy stored", "Status"

### Avoid special characters

Do not use parentheses, brackets, or other special characters in display names.
These characters can interfere with entity ID generation and cause issues.

❌ Bad: "Power (Source to Target)", "Max Import Price (Shadow)"
✅ Good: "\{source} to \{target} power", "Max import power shadow price"

### Parameterized translations

Connection sensors use `{source}` and `{target}` placeholders to display the names of the elements they join:

```json
{
  "entity": {
    "sensor": {
      "connection_power": {
        "name": "{source} to {target} power"
      }
    }
  }
}
```

Every entity of an element gets its placeholders from `build_translation_placeholders()` in [`entities/translation_placeholders.py`](../../../custom_components/haeo/entities/translation_placeholders.py).
Every configured field is available by its name, including fields inside sections, and `name` defaults to the element's title.
Parameterize a string with these placeholders rather than writing one string per element type.

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

---
applyTo: '**'
description: Playwright MCP browser automation patterns for Home Assistant
globs: ['**']
alwaysApply: false
---

# Playwright MCP Browser Automation

Patterns for browser automation using the Playwright MCP server with Home Assistant.

## Core Concept: Snapshot-Based Interaction

The MCP pattern uses accessibility tree snapshots instead of CSS selectors.

**Workflow:**

1. Capture snapshot with `browser_snapshot()`
2. Parse element refs from YAML output
3. Interact using `browser_click(ref=...)` or `browser_type(ref=..., text=...)`
4. Re-snapshot after each interaction (refs change)

**Snapshot element format:**

```yaml
button "Submit" [ref=e5355] [cursor=pointer]:
  - generic [ref=e5356]: Submit
```

The `ref` attribute uniquely identifies elements for the current page state.

## Environment Setup

### Starting Home Assistant

```bash
uv run hass -c config
```

Wait 30-60 seconds for startup. UI available at `http://localhost:8123`.

### Resetting to Clean State

```bash
git clean -fdX config/
```

Removes database, state files, and cached data while preserving tracked sensor packages.

## Element Identification

Identify elements in snapshots by:

| Pattern          | Example                                |
| ---------------- | -------------------------------------- |
| Role and name    | `button "Submit" [ref=e5355]`          |
| Text content     | `generic [ref=e733]: Sigenergy System` |
| Nested structure | Parent-child hierarchy in YAML         |

## UI Component Patterns

### Text Input (textbox)

```yaml
textbox "Load Name*" [ref=e5331]:
  - text: Load
```

```
browser_type(element="Load Name textbox", ref="e5331", text="My Load")
```

### Button

```yaml
button "Submit" [ref=e5355] [cursor=pointer]:
  - generic: Submit
```

```
browser_click(element="Submit button", ref="e5355")
```

### Combobox Dropdown

**Closed state:**

```yaml
combobox "Connection*" [ref=e5337]:
  - generic: Switchboard
```

**Pattern:**

1. Click combobox to open
2. Re-snapshot to see options
3. Click option ref

```
browser_click(element="Connection combobox", ref="e5337")
# snapshot shows: option "Inverter" [ref=e5361]
browser_click(element="Inverter option", ref="e5361")
```

### Entity Picker Dialog

Entity pickers open a dialog with search and results.

**Closed state:**

```yaml
listitem [ref=e5348]:
  - generic: Select an entity
```

**Pattern:**

1. Click listitem to open picker dialog
2. Type in Search textbox to filter
3. Click matching sensor in results

```
browser_click(element="Entity picker", ref="e5348")
# dialog opens with: textbox "Search" [ref=e5378]
browser_type(element="Search textbox", ref="e5378", text="General Price")
# results show: listitem [ref=e5650]: Home - General Price
browser_click(element="Home - General Price", ref="e5650")
```

**Search behavior:**

- Matches **friendly names**, not entity_ids
- Use distinctive keywords: "General Price", "consumed", "charging"
- Partial matches work: "solar" finds all solar sensors

### Multi-Select Entity Picker

For fields accepting multiple sensors, an "Add entity" button appears after first selection.

```
# Select first
browser_click(element="Forecast picker", ref="e5348")
browser_type(element="Search", ref="e5378", text="East solar")
browser_click(element="East solar sensor", ref="e5650")

# Add more
browser_click(element="Add entity button", ref="e5975")
browser_type(element="Search", ref="e5378", text="North solar")
browser_click(element="North solar sensor", ref="e5651")
```

### Numeric Input (spinbutton)

```yaml
spinbutton "Import Limit" [ref=e5400]
...
```

```
browser_type(element="Import Limit", ref="e5400", text="55")
```

### Alert Dialog

Success dialogs block all other interactions until closed.

```yaml
alertdialog "Success" [ref=e6060]:
  - paragraph: Created configuration for Load.
  - button "Finish" [ref=e6067]
```

**Always close immediately:**

```
browser_click(element="Finish button", ref="e6067")
```

## Critical Rules

### Re-snapshot After Every Interaction

Element refs change after any interaction.

```
browser_click(element="Submit", ref="e5355")
browser_snapshot()  # REQUIRED - get new refs
browser_click(element="Finish", ref="e6067")  # New ref from new snapshot
```

### Close Dialogs Before Continuing

Unacknowledged success dialogs block all subsequent interactions.
Look for `alertdialog` in snapshot and click Finish/Close.

### Search by Friendly Name

Entity picker search matches friendly names, not entity_ids.

✅ `"General Price"` → matches "Home - General Price"
✅ `"max active power"` → matches "Sigen Plant Max Active Power"
❌ `"sensor.home_general_price"` → no match

### Descriptive Element Names

Always provide meaningful `element` descriptions.

✅ `browser_click(element="Connection combobox", ref="e5337")`
❌ `browser_click(element="combobox", ref="e5337")`

## Navigation

| Page                 | URL                                                            |
| -------------------- | -------------------------------------------------------------- |
| Home                 | `http://localhost:8123`                                        |
| Integrations         | `http://localhost:8123/config/integrations`                    |
| Specific integration | `http://localhost:8123/config/integrations/integration/{name}` |

```
browser_navigate(url="http://localhost:8123/config/integrations")
```

## Troubleshooting

### No Search Results

- Try broader search terms
- Search matches friendly names only
- Check available sensors in config/packages/

### Dialog Blocking

Take snapshot, find `alertdialog`, click its Finish/Close button.

### Wrong Element Clicked

Using stale ref from old snapshot. Always re-snapshot after interactions.

### Element Not Found

Element may not be visible. Check if scrolling needed or if it's in a closed dropdown/dialog.

## Common Snapshot Patterns

| Component      | Pattern                                                 |
| -------------- | ------------------------------------------------------- |
| Text input     | `textbox "Field*" [ref=...]`                            |
| Button         | `button "Text" [ref=...]`                               |
| Dropdown       | `combobox "Field*" [ref=...]`                           |
| Entity picker  | `listitem: Select an entity`                            |
| Success dialog | `alertdialog "Success"`                                 |
| Numeric input  | `spinbutton "Field" [ref=...]`                          |
| Option in list | `option "Name" [ref=...]` or `listitem [ref=...]: Name` |

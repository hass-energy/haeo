# Home Assistant Browser Automation Guide

Structured patterns for interacting with Home Assistant UI components through Playwright.

## Status

**Successfully tested:**
- ✅ Complete onboarding flow
- ✅ Login
- ✅ Add HAEO integration
- ✅ Add Node elements (DC Net, AC Net)
- ✅ Add Battery element (with sensors)
- ✅ Entity picker with `ha-combo-box-textfield input` selector
- ✅ Dropdown selectors with `:has-text()`

**Challenges:**
- ⚠️ Entity picker scrolling (results virtualized)
- ⚠️ Search literal prefix matching (breaks at `-`)
- ⚠️ Multiple sensor selection (8 forecast sensors for solar)

## UI Component Patterns

### Text Input Fields

**When to use:** Form fields with `name` attribute

**Selector:** `input[name="field_name"]`

**Example:**
```javascript
playwright_fill({ selector: "input[name=\"username\"]", value: "testuser" })
playwright_fill({ selector: "input[name=\"name\"]", value: "Battery" })
```

**Common fields:**
- `input[name="name"]` - Name field in forms
- `input[name="username"]` - Username for login
- `input[name="password"]` - Password fields

---

### Buttons

**When to use:** Clicking buttons with visible text

**Selector:** `text=Button Text`

**Why:** Text selectors automatically pierce shadow DOM

**Example:**
```javascript
playwright_click({ selector: "text=Submit" })
playwright_click({ selector: "text=Next" })
playwright_click({ selector: "text=Finish" })
```

**Common buttons:**
- `text=Submit` - Form submission
- `text=Next` - Wizard navigation
- `text=Finish` - Confirmation dialogs
- `text=Create account` - User creation

---

### Dropdown Selectors (`ha-select`)

**When to use:** Selecting from dropdown lists (e.g., Connection field)

**Pattern:**
1. Open: `ha-select`
2. Select: `ha-list-item:has-text("Option")`

**Why `:has-text()`:** Prevents timeout from multiple text matches

**Example:**
```javascript
// Open connection dropdown
playwright_click({ selector: "ha-select" })

// Select DC Net
playwright_click({ selector: "ha-list-item:has-text(\"DC Net\")" })
```

**Common options:**
- "Switchboard"
- "DC Net"
- "AC Net"

---

### Entity Picker Dialogs

**When to use:** Selecting sensors or entities

**Pattern:**
1. Open: `ha-picker-field[aria-label="Field Name"]`
2. Search: `ha-combo-box-textfield input`
3. Select: `text=Entity Name`

**Key selector:** `ha-combo-box-textfield input` is unique to entity picker dialogs

**Example:**
```javascript
// Open capacity picker
playwright_click({ selector: "ha-picker-field[aria-label=\"Capacity\"]" })

// Search for sensor
playwright_fill({
  selector: "ha-combo-box-textfield input",
  value: "rated_energy_capacity"
})

// Select from results
playwright_click({ selector: "text=Sigen Plant Rated Energy Capacity" })
```

**Common pickers:**
- `ha-picker-field[aria-label="Capacity"]`
- `ha-picker-field[aria-label="Current Charge Sensor"]`
- `ha-picker-field[aria-label="Maximum Charge Power"]`
- `ha-picker-field[aria-label="Maximum Discharge Power"]`

**Tips:**
- Search is literal prefix match, not fuzzy search
- Search breaks at special characters like `-` (text after `-` is ignored)
- Use full unique prefix: "East solar production forecast Estimated energy production"
- Results are in `vaadin-combo-box-scroller` which may need scrolling
- Scroll scroller to top before selecting: `document.querySelector('vaadin-combo-box-scroller').scrollTop = 0`

**Scrolling results:**
```javascript
playwright_evaluate({
  script: "(function() { const scroller = document.querySelector('vaadin-combo-box-scroller'); if (scroller) { scroller.scrollTop = 0; return 'Scrolled'; } return 'Not found'; })()"
})
```

---

### Icon Buttons

**When to use:** Menu buttons (three dots ⋮)

**Selector:** `ha-icon-button`

**Warning:** Clicks first match - be aware of context

**Example:**
```javascript
// Open menu
playwright_click({ selector: "ha-icon-button" })
```

---

### Element Type Buttons (HAEO)

**When to use:** Adding elements to HAEO network

**Two approaches:**

**1. Top buttons** (may be disabled if hub has issues):
```javascript
playwright_click({ selector: "text=Node" })
playwright_click({ selector: "text=Battery" })
```

**2. Menu** (always available):
```javascript
playwright_click({ selector: "ha-icon-button" })
playwright_click({ selector: "text=Battery" })
```

**Available types:**
- Node
- Battery
- Photovoltaics
- Grid Connection
- Load
- Connection
- Inverter

---

## Process Flows

### Complete Onboarding

```javascript
// 1. Navigate
playwright_navigate({ url: "http://localhost:8123" })

// 2. Start onboarding
playwright_click({ selector: "ha-button" })

// 3. Create user
playwright_fill({ selector: "input[name=\"name\"]", value: "User Name" })
playwright_fill({ selector: "input[name=\"username\"]", value: "username" })
playwright_fill({ selector: "input[name=\"password\"]", value: "password" })
playwright_fill({ selector: "input[name=\"password_confirm\"]", value: "password" })
playwright_click({ selector: "text=Create account" })

// 4. Complete steps
playwright_click({ selector: "text=Next" }) // Location
playwright_click({ selector: "text=Next" }) // Country
playwright_click({ selector: "text=Next" }) // Analytics
playwright_click({ selector: "text=Finish" }) // Integrations

// 5. Login
playwright_fill({ selector: "input[name=\"username\"]", value: "username" })
playwright_fill({ selector: "input[name=\"password\"]", value: "password" })
playwright_click({ selector: "text=Log in" })
```

---

### Add HAEO Integration

```javascript
// 1. Navigate to integrations
playwright_navigate({ url: "http://localhost:8123/config/integrations" })

// 2. Add integration
playwright_click({ selector: "text=Add integration" })
playwright_fill({ selector: "input[placeholder*=\"Search\"]", value: "HAEO" })
playwright_click({ selector: "text=Home Assistant Energy Optimizer" })

// 3. Configure network
playwright_fill({ selector: "input[name=\"name\"]", value: "Sigenergy System" })
playwright_click({ selector: "text=Submit" })

// 4. CRITICAL: Close confirmation
playwright_click({ selector: "text=Finish" })
```

---

### Add Node Element

```javascript
// 1. Click Node button (or use menu if disabled)
playwright_click({ selector: "text=Node" })

// 2. Fill name
playwright_fill({ selector: "input[name=\"name\"]", value: "DC Net" })

// 3. Submit
playwright_click({ selector: "text=Submit" })

// 4. CRITICAL: Close confirmation
playwright_click({ selector: "text=Finish" })
```

---

### Add Battery Element

```javascript
// 1. Open Battery configuration
playwright_click({ selector: "text=Battery" })

// 2. Fill name
playwright_fill({ selector: "input[name=\"name\"]", value: "Battery" })

// 3. Select connection
playwright_click({ selector: "ha-select" })
playwright_click({ selector: "ha-list-item:has-text(\"DC Net\")" })

// 4. Select capacity sensor
playwright_click({ selector: "ha-picker-field[aria-label=\"Capacity\"]" })
playwright_fill({ selector: "ha-combo-box-textfield input", value: "rated_energy_capacity" })
playwright_click({ selector: "text=Sigen Plant Rated Energy Capacity" })

// 5. Select SOC sensor
playwright_click({ selector: "ha-picker-field[aria-label=\"Current Charge Sensor\"]" })
playwright_fill({ selector: "ha-combo-box-textfield input", value: "state_of_charge" })
playwright_click({ selector: "text=Sigen Plant Battery State of Charge" })

// 6. Select max charge power
playwright_click({ selector: "ha-picker-field[aria-label=\"Maximum Charge Power\"]" })
playwright_fill({ selector: "ha-combo-box-textfield input", value: "charging" })
playwright_click({ selector: "text=Sigen Plant Ess Rated Charging Power" })

// 7. Scroll to see discharge power field
playwright_evaluate({ script: "(function() { window.scrollBy(0, 300); })()" })

// 8. Select max discharge power
playwright_click({ selector: "ha-picker-field[aria-label=\"Maximum Discharge Power\"]" })
playwright_fill({ selector: "ha-combo-box-textfield input", value: "discharging" })
playwright_click({ selector: "text=Sigen Plant Ess Rated Discharging Power" })

// 9. Submit
playwright_click({ selector: "text=Submit" })

// 10. CRITICAL: Close confirmation
playwright_click({ selector: "text=Finish" })
```

---

## Critical Rules

### 1. Always Close Dialogs

After submitting any form, a "Devices created" dialog appears.

**MUST DO:**
```javascript
playwright_click({ selector: "text=Finish" })
```

**Why:** Unacknowledged dialogs block ALL subsequent interactions with "intercepts pointer events" errors.

---

### 2. Scroll Before Clicking

Elements must be visible on screen before clicking.

**Pattern:**
```javascript
playwright_evaluate({ script: "(function() { window.scrollBy(0, 300); })()" })
```

**When needed:**
- Long forms with many fields
- Dropdown options not visible
- Buttons below fold

---

### 3. Use Correct Entity Picker Selector

**✅ CORRECT:**
```javascript
playwright_fill({ selector: "ha-combo-box-textfield input", value: "search" })
```

**❌ WRONG:**
```javascript
playwright_fill({ selector: "input[aria-labelledby=\"label\"]", value: "search" })
// This matches BOTH form inputs AND dialog inputs!
```

---

### 4. Use `:has-text()` for List Items

**✅ CORRECT:**
```javascript
playwright_click({ selector: "ha-list-item:has-text(\"DC Net\")" })
```

**❌ WRONG:**
```javascript
playwright_click({ selector: "text=DC Net" })
// Matches multiple elements, causes 30s timeout
```

---

### 5. Distinguish "Add" Contexts

- `text=Add hub` - Creates NEW network (avoid unless intended)
- Menu `text=Battery` - Adds element to existing network (correct)
- `text=Add integration` - Adds integration to HA (different context)

---

## Troubleshooting

### "Intercepts pointer events" Error

**Cause:** Unacknowledged dialog blocking interactions

**Solution:**
1. Take screenshot
2. Find dialog with `text=Finish`, `text=Close`, or `text=OK`
3. Close it
4. Continue

---

### 30-Second Timeout

**Causes:**
1. Selector matches multiple elements
2. Element not visible (need scroll)
3. Wrong selector
4. Element doesn't exist

**Solutions:**
1. Use `:has-text()` for specificity
2. Scroll element into view
3. Take screenshot to verify
4. Check selector in documentation

---

### Filled Wrong Input

**Cause:** Ambiguous selector matching multiple inputs

**Solution:** Use more specific selector
- ✅ `ha-combo-box-textfield input` (dialog only)
- ❌ `input[aria-labelledby="label"]` (matches many)

---

### Buttons Greyed Out

**Cause:** Hub has repair issues

**Solution:** Use menu instead of top buttons
```javascript
playwright_click({ selector: "ha-icon-button" })
playwright_click({ selector: "text=Battery" })
```

---

## Quick Reference

### Navigation URLs
- Integrations: `http://localhost:8123/config/integrations`
- Settings: `http://localhost:8123/config`

### Common Selectors
- Name input: `input[name="name"]`
- Submit: `text=Submit`
- Finish dialog: `text=Finish`
- Connection dropdown: `ha-select`
- Entity picker: `ha-picker-field[aria-label="Field Name"]`
- Entity search: `ha-combo-box-textfield input`
- Menu button: `ha-icon-button`

### Integration Names
- Technical: HAEO
- Display: "Home Assistant Energy Optimizer"

---

## Key Principles

1. **Text selectors pierce shadow DOM** - Use them for buttons
2. **Name attributes are reliable** - Use for form inputs
3. **Always close dialogs** - Prevents blocking errors
4. **Scroll before clicking** - Ensures visibility
5. **Use specific selectors** - Avoid ambiguity
6. **Menu over buttons** - Menu always works
7. **Take screenshots when stuck** - See actual state

---

## Known Challenges

### Entity Picker Scrolling

**Issue:** Entity picker results are virtualized in `vaadin-combo-box-scroller`
- Only ~10 items visible at once
- Must scroll to find sensors not in initial view
- Clicking invisible items fails silently or times out

**Solution:** Scroll scroller element before clicking:
```javascript
playwright_evaluate({
  script: "(function() { document.querySelector('vaadin-combo-box-scroller').scrollTop = 0; })()"
})
```

### Search Behavior

**Issue:** Search is literal prefix match, not fuzzy
- Breaks at special characters like `-`
- "East today" doesn't match "East solar production forecast Estimated energy production - today"
- Must use full unique prefix before special characters

**Solution:** Use complete prefix up to the distinguishing part:
- ✅ "East solar production forecast Estimated energy production"
- ❌ "East today"

### Multiple Sensor Selection

**Issue:** Adding multiple sensors (e.g., 8 forecast sensors for solar) requires:
1. Click "Select an entity" for each
2. Search for sensor
3. Scroll results if needed
4. Click sensor
5. Repeat

**Complexity:** High error rate due to scrolling and similar sensor names

---

## References

- Preconfigured sensors: `config/packages/`
- Translation keys: `custom_components/haeo/translations/en.json`
- Demo guide: `docs/user-guide/examples/sigenergy-system.md`
- Get sensor friendly names: `jq -r '.attributes.friendly_name' config/packages/*/sensor_name.json`

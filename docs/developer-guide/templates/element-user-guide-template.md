# [Element Name]

Brief description of the element (1-2 sentences).
Focus on what the element represents in the energy system and its primary purpose.

!!! note "Elements and devices"

    A single element configuration may create multiple devices in Home Assistant.
    See [Sensors Created](#sensors-created) for the devices and sensors this element produces.
    For mathematical details, see the [Model Layer documentation](../../modeling/index.md).

## Configuration Fields

Provide a table listing all configuration fields with their types, requirements, and descriptions.
Link to the [Forecasts and Sensors guide](../../user-guide/forecasts-and-sensors.md) for sensor field types.

| Field             | Type                                                | Required | Default | Description                        |
| ----------------- | --------------------------------------------------- | -------- | ------- | ---------------------------------- |
| **name**          | string                                              | Yes      | -       | Unique identifier for this element |
| **field_example** | [sensor](../../user-guide/forecasts-and-sensors.md) | No       | -       | Example sensor field description   |

### Field-Specific Notes

Add H3 subsections for fields that need additional explanation.
Keep explanations focused on configuration, not mathematical modeling.

For complex elements, you may group related fields under a descriptive H3 heading, then use H4 subheadings for individual field details.
Link to the field name in the configuration table where appropriate.

## Configuration Examples

Provide minimal working examples using table format.
Keep examples realistic and representative of typical use cases.
For complex elements, provide multiple examples showing different configuration patterns.

### Basic Configuration

| Field         | Value                |
| ------------- | -------------------- |
| **Name**      | Example Element      |
| **Field One** | value                |
| **Field Two** | sensor.example_value |

### Alternative Configuration

| Field         | Value                     |
| ------------- | ------------------------- |
| **Name**      | Alternative Example       |
| **Field One** | different_value           |
| **Field Two** | sensor.alternative_sensor |

## Sensors Created

This element creates sensors organized by device.
Each device groups related sensors for a specific aspect of the element's operation.

For detailed mathematical formulation, see the [relevant Model Layer documentation](../../modeling/index.md).

### [Device Name] Device

Brief description of what this device represents.

| Sensor                                                | Unit  | Description                            |
| ----------------------------------------------------- | ----- | -------------------------------------- |
| [`sensor.{name}_sensor_one`](#sensor-one)             | kW    | Brief description (link to subsection) |
| [`sensor.{name}_sensor_two`](#sensor-two)             | kWh   | Brief description (link to subsection) |
| [`sensor.{name}_shadow_price_one`](#shadow-price-one) | \$/kW | Brief description (shadow price)       |

### [Optional Device Name] Device (\*)

Brief description of when this device is created and what it represents.

(\*) Only created when [specific condition is met]

| Sensor                                                    | Unit | Description                            |
| --------------------------------------------------------- | ---- | -------------------------------------- |
| [`sensor.{name}_conditional_sensor`](#conditional-sensor) | %    | Brief description (conditional sensor) |

---

### Sensor Descriptions

#### Sensor One

Plain-English explanation of what this sensor represents and what its values mean.
Keep explanations focused on interpretation, not mathematical details.

**Example interpretation**: "A value of 5.2 kW means..."

#### Sensor Two

Plain-English explanation of what this sensor represents and what its values mean.

#### Conditional Sensor

Plain-English explanation of when this sensor is created and what it represents.

**Availability**: This sensor only appears when [specific condition].

#### Shadow Price One

Brief explanation of what this specific shadow price represents.
Reference the [Shadow Prices modeling guide](../../modeling/shadow-prices.md) for general shadow price concepts.

**Interpretation**:

- **Zero value**: Constraint is not limiting (explain what this means for this element)
- **Nonzero value**: Constraint is binding (explain what this means for this element)

---

All sensors include a `forecast` attribute containing future optimized values for upcoming periods.

## Troubleshooting

List common configuration issues and their solutions.
Focus on actionable problems users are likely to encounter.

### Issue Name

**Problem**: Brief description of the issue

**Solution**: Clear steps to resolve the issue

## Next Steps

!!! note "Template Instructions"

    Curate 3-4 Next Steps cards that are most relevant for users who just configured this element.
    Below are example cards showing the structure—replace them with actual links and content.
    Consider: connecting to other elements, understanding related concepts, related element types, or troubleshooting.

    Example patterns for element configuration pages:

    - **Connections**: Link to `connections.md` to explain network connectivity
    - **Forecasts/Sensors**: Link to `../forecasts-and-sensors.md` for sensor field details
    - **Related elements**: Link to complementary elements (battery→grid, solar→battery, etc.)
    - **Optimization**: Link to `../optimization.md` to explain how this element affects results

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **[Card Title]**

    ---

    Brief description of what the user will learn or accomplish.

    [:material-arrow-right: Link text](#)

- :material-chart-line:{ .lg .middle } **[Card Title]**

    ---

    Brief description of what the user will learn or accomplish.

    [:material-arrow-right: Link text](#)

- :material-battery-charging:{ .lg .middle } **[Card Title]**

    ---

    Brief description of what the user will learn or accomplish.

    [:material-arrow-right: Link text](#)

</div>

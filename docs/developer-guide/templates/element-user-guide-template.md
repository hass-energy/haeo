# [Element Name] Configuration

Brief description of the element (1-2 sentences).
Focus on what the element represents in the energy system and its primary purpose.

## Configuration Fields

Provide a table listing all configuration fields with their types, requirements, and descriptions.
Link to the [Forecasts and Sensors guide](../../user-guide/forecasts-and-sensors.md) for sensor field types.

| Field             | Type                                                | Required | Default | Description                        |
| ----------------- | --------------------------------------------------- | -------- | ------- | ---------------------------------- |
| **name**          | string                                              | Yes      | -       | Unique identifier for this element |
| **field_example** | [sensor](../../user-guide/forecasts-and-sensors.md) | No       | -       | Example sensor field description   |

### Field-Specific Notes

Add subsections for any fields that need additional explanation.
Keep explanations focused on configuration, not mathematical modeling.

## Configuration Example

Provide a minimal working example without detailed explanations.
Keep examples realistic and representative of typical use cases.

```yaml
haeo:
  elements:
    - type: element_type
      name: example_element
      field_one: value
      field_two: sensor.example
```

## Sensors Created

List all sensors that this element creates, their units, and what they represent.
Use a consistent table format.

| Sensor Name               | Unit | Description               |
| ------------------------- | ---- | ------------------------- |
| `element_name_sensor_one` | Unit | What this sensor measures |
| `element_name_sensor_two` | Unit | What this sensor measures |

## Troubleshooting

List common configuration issues and their solutions.
Focus on actionable problems users are likely to encounter.

### Issue Name

**Problem**: Brief description of the issue

**Solution**: Clear steps to resolve the issue

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connect to network**

    ---

    Learn how to connect this element to other elements in the network.

    [:material-arrow-right: Network connections](../../user-guide/elements/connections.md)

- :material-chart-line:{ .lg .middle } **Understand sensor loading**

    ---

    Deep dive into how HAEO loads and processes sensor data.

    [:material-arrow-right: Forecasts and sensors](../../user-guide/forecasts-and-sensors.md)

- :material-help-circle:{ .lg .middle } **Troubleshooting**

    ---

    Common issues and solutions for HAEO configuration.

    [:material-arrow-right: Troubleshooting guide](../../user-guide/troubleshooting.md)

</div>

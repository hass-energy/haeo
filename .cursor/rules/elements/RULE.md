---
description: "Energy elements layer development"
globs: ["custom_components/haeo/elements/**"]
alwaysApply: false
---

# Elements layer development

The elements layer bridges Home Assistant configuration with the LP model layer.

## Element responsibilities

Each element (Battery, Grid, Load, Photovoltaics, Node):
- Loads data from Home Assistant sensors
- Creates corresponding model layer elements
- Extracts optimization results back to HA sensors

## Data loading

- Use the data loading utilities in `data/`
- Handle missing sensor data gracefully
- Validate loaded data before passing to model

## Model creation

- Create model elements with appropriate parameters
- Map HA configuration to model parameters
- Use SI units when creating model elements (convert from user input if needed)

## Result extraction

- Extract optimization results from model
- Create sensors to expose results to HA
- Use appropriate device classes and units for sensors

## Sensor patterns

- Use generic property detection instead of element type checking
- Use translation keys for sensor names
- Set appropriate entity categories (e.g., DIAGNOSTIC for internal values)

## Error handling

- Catch data loading failures
- Set element as unavailable when data is missing
- Log meaningful error messages

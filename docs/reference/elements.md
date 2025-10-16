# Element Type Reference

## Element Types

| Element       | Direction     | Storage | Forecasts      | Complexity | Typical Use                |
| ------------- | ------------- | ------- | -------------- | ---------- | -------------------------- |
| Battery       | Bidirectional | Yes     | SOC sensor     | Medium     | Home batteries, EV storage |
| Grid          | Bidirectional | No      | Price sensors  | Simple     | Utility import/export      |
| Photovoltaics | Generation    | No      | Solar forecast | Simple     | Rooftop solar, arrays      |
| Constant Load | Consumption   | No      | None           | Simple     | Baseline loads             |
| Forecast Load | Consumption   | No      | Load forecast  | Medium     | Variable consumption       |
| Node          | Pass-through  | No      | None           | Simple     | Balance points             |

## Element Selection

**I need to model...**

- Utility connection → Grid
- Solar panels → Photovoltaics
- Battery system → Battery
- Always-on devices → Constant Load
- Variable usage → Forecast Load
- Connection hub → Node

## Capabilities

| Element       | Decision Variables          | Constraints                             |
| ------------- | --------------------------- | --------------------------------------- |
| Battery       | Charge, discharge, energy   | Power limits, SOC range, energy balance |
| Grid          | Import, export              | Optional power limits                   |
| Photovoltaics | Generation (if curtailment) | Non-negativity, forecast bound          |
| Constant Load | None (parameter)            | Fixed value                             |
| Forecast Load | None (parameter)            | Follows forecast                        |
| Node          | None (enforces balance)     | Power balance (Kirchhoff's law)         |

## Configuration Details

For full configuration guide, see:

- [Battery Configuration](../user-guide/elements/battery.md)
- [Grid Configuration](../user-guide/elements/grid.md)
- [Photovoltaics Configuration](../user-guide/elements/photovoltaics.md)
- [Load Configuration](../user-guide/elements/constant-load.md)
- [Node Configuration](../user-guide/elements/node.md)

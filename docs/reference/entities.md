# Entity Type Reference

## Entity Types

| Entity | Direction | Storage | Forecasts | Complexity | Typical Use |
|--------|-----------|---------|-----------|------------|-------------|
| Battery | Bidirectional | Yes | SOC sensor | Medium | Home batteries, EV storage |
| Grid | Bidirectional | No | Price sensors | Simple | Utility import/export |
| Photovoltaics | Generation | No | Solar forecast | Simple | Rooftop solar, arrays |
| Constant Load | Consumption | No | None | Simple | Baseline loads |
| Forecast Load | Consumption | No | Load forecast | Medium | Variable consumption |
| Net | Pass-through | No | None | Simple | Balance points |

## Entity Selection

**I need to model...**

- Utility connection → Grid
- Solar panels → Photovoltaics
- Battery system → Battery
- Always-on devices → Constant Load
- Variable usage → Forecast Load
- Connection hub → Net

## Capabilities

| Entity | Decision Variables | Constraints |
|--------|-------------------|-------------|
| Battery | Charge, discharge, energy | Power limits, SOC range, energy balance |
| Grid | Import, export | Optional power limits |
| Photovoltaics | Generation (if curtailment) | Non-negativity, forecast bound |
| Constant Load | None (parameter) | Fixed value |
| Forecast Load | None (parameter) | Follows forecast |
| Net | None (enforces balance) | Power balance (Kirchhoff's law) |

## Configuration Details

For full configuration guide, see:

- [Battery Configuration](../user-guide/entities/battery.md)
- [Grid Configuration](../user-guide/entities/grid.md)
- [Photovoltaics Configuration](../user-guide/entities/photovoltaics.md)
- [Load Configuration](../user-guide/entities/loads.md)
- [Net Configuration](../user-guide/entities/net.md)

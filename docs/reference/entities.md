# Entity Type Reference

Complete reference for all entity types supported by HAEO.

## Entity Types

| Entity        | Power Direction | Storage | Forecasts      | Typical Use                   |
| ------------- | --------------- | ------- | -------------- | ----------------------------- |
| Battery       | Bidirectional   | Yes     | SOC sensor     | Home batteries, EV storage    |
| Grid          | Bidirectional   | No      | Price sensors  | Grid import/export            |
| Photovoltaics | Generation      | No      | Solar forecast | Rooftop solar, ground mount   |
| Constant Load | Consumption     | No      | None           | Base loads, always-on devices |
| Forecast Load | Consumption     | No      | Load forecast  | Household consumption         |
| Net           | Pass-through    | No      | None           | Virtual power balance nodes   |

## Configuration Details

See individual entity pages for detailed configuration:

- [Battery Configuration](../user-guide/entities/battery.md)
- [Grid Configuration](../user-guide/entities/grid.md)
- [Photovoltaics Configuration](../user-guide/entities/photovoltaics.md)
- [Load Configuration](../user-guide/entities/loads.md)
- [Net Configuration](../user-guide/entities/net.md)

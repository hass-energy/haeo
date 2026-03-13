# HAEO forecast card

The HAEO forecast card is a custom Lovelace card that renders HAEO `forecast` attributes as a fast interactive SVG chart.
It is designed for fixed-horizon data and uses a MobX state model so hover and timeline updates stay responsive.

## What the card shows

The card reads `forecast` attributes from HAEO output sensors.
It automatically groups series into lanes (`power`, `price`, `soc`, `shadow`, `other`).
Power and price series are drawn with step-post semantics.
State-of-charge series are drawn as continuous lines.

## Prerequisites

You must already have the HAEO integration installed and running.
At least one HAEO output sensor must expose a `forecast` attribute.

## Add the card resource

The integration serves the card bundle at:

`/haeo-static/haeo-forecast-card.js`

Add this as a Lovelace resource:

1. Open **Settings -> Dashboards -> Resources**.
2. Add a new resource URL: `/haeo-static/haeo-forecast-card.js`.
3. Set resource type to **JavaScript module**.

## Basic card config

```yaml
type: custom:haeo-forecast-card
title: HAEO forecast
entities:
  - sensor.haeo_grid_import_power
  - sensor.haeo_grid_export_power
  - sensor.haeo_battery_state_of_charge
```

## Configuration options

- `type`: Must be `custom:haeo-forecast-card`.
- `title`: Optional card title.
- `entities`: Optional list of forecast sensor entities.
  If omitted, the card auto-discovers entities with a `forecast` attribute.
- `height`: Optional chart height in pixels.
- `animation_mode`: `off`, `reduced`, or `smooth`.
- `animation_speed`: Relative timeline slide speed (default `1`).

## Interaction features

- Hover crosshair with nearest-point value snapping.
- Tooltip with per-series values and per-lane totals.
- Legend hover highlighting.
- Automatic scaling based on card dimensions.
- Smooth time sliding between forecast updates.

## Troubleshooting

If no data appears:

- Confirm your selected entity IDs exist.
- Confirm each entity has a populated `forecast` attribute.
- Confirm the Lovelace resource URL is exactly `/haeo-static/haeo-forecast-card.js`.

## Next steps

<div class="grid cards" markdown>

-   :material-chart-timeline-variant:{ .lg .middle } **Understand forecast sensors**

    ---

    Learn how HAEO forecast attributes are produced and interpreted.

    [:material-arrow-right: Forecasts and sensors](forecasts-and-sensors.md)

-   :material-robot:{ .lg .middle } **Automate with HAEO outputs**

    ---

    Use forecast and optimization outputs in automations.

    [:material-arrow-right: Automation examples](automations.md)

</div>

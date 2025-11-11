# Configuration Schema Reference

Complete configuration schema for all HAEO entities.

## Network Configuration

| Field          | Type            | Required | Default | Description               |
| -------------- | --------------- | -------- | ------- | ------------------------- |
| Name           | string          | Yes      | -       | Unique network identifier |
| Horizon Hours  | integer (1-168) | Yes      | 48      | Optimization time horizon |
| Period Minutes | integer (1-60)  | Yes      | 5       | Time step size            |

## Sensor Field Behavior

Fields annotated with **sensor(s)** accept one or more Home Assistant sensor entity IDs.

### Data Extraction

The `TimeSeriesLoader` processes sensor references:

1. Reads each sensor's current value (present value)
2. Detects and parses any forecast data in sensor attributes
3. Combines multiple sensors by summing present values and merging forecasts
4. Interpolates and fuses data to produce values aligned with the optimization horizon

### Single vs Multiple Sensors

- **Single sensor**: `sensor.electricity_price` - One entity ID
- **Multiple sensors**: `["sensor.price_today", "sensor.price_tomorrow"]` - List of entity IDs

Multiple sensors are combined additively (values sum at each timestamp).

For details on sensor behavior, see the [Forecasts and Sensors guide](../user-guide/forecasts-and-sensors.md).

## Battery Configuration

| Field                     | Type           | Required | Default | Description               |
| ------------------------- | -------------- | -------- | ------- | ------------------------- |
| Name                      | string         | Yes      | -       | Unique identifier         |
| Capacity                  | float (kWh)    | Yes      | -       | Total capacity            |
| Initial Charge Percentage | sensor         | Yes      | -       | SOC sensor entity ID      |
| Min Charge Percentage     | float (%)      | No       | 10      | Minimum SOC               |
| Max Charge Percentage     | float (%)      | No       | 90      | Maximum SOC               |
| Efficiency                | float (%)      | No       | 99      | Round-trip efficiency     |
| Max Charge Power          | float (kW)     | No       | -       | Max charge rate           |
| Max Discharge Power       | float (kW)     | No       | -       | Max discharge rate        |
| Charge Cost               | float (\$/kWh) | No       | 0       | Additional charge cost    |
| Discharge Cost            | float (\$/kWh) | No       | 0       | Additional discharge cost |

## Grid Configuration

| Field        | Type       | Required | Default | Description           |
| ------------ | ---------- | -------- | ------- | --------------------- |
| Name         | string     | Yes      | -       | Unique identifier     |
| Import Price | sensor(s)  | Yes      | -       | Import price (\$/kWh) |
| Export Price | sensor(s)  | Yes      | -       | Export price (\$/kWh) |
| Import Limit | float (kW) | No       | -       | Max import power      |
| Export Limit | float (kW) | No       | -       | Max export power      |

Import and Export Price fields accept one or more sensor entity IDs.
Multiple price sensors are combined additively.

## Photovoltaics Configuration

| Field            | Type           | Required | Default | Description            |
| ---------------- | -------------- | -------- | ------- | ---------------------- |
| Name             | string         | Yes      | -       | Unique identifier      |
| Forecast         | sensor(s)      | Yes      | -       | Solar forecast sensors |
| Production Price | float (\$/kWh) | No       | 0       | Value of generation    |
| Curtailment      | boolean        | No       | false   | Allow curtailment      |

The Forecast field accepts one or more sensor entity IDs.
Multiple solar forecast sensors are combined additively.

## Load Configuration

| Field    | Type      | Required | Default | Description                 |
| -------- | --------- | -------- | ------- | --------------------------- |
| Name     | string    | Yes      | -       | Unique identifier           |
| Forecast | sensor(s) | Yes      | -       | Power consumption sensor(s) |

The Forecast field accepts one or more sensor entity IDs providing power consumption data.
For constant loads, use an `input_number` helper.
For variable loads, use sensors with forecast data.

See the [Forecasts and Sensors guide](../user-guide/forecasts-and-sensors.md) for details on how multiple sensors are combined.

## Connection Configuration

| Field     | Type       | Required | Default | Description        |
| --------- | ---------- | -------- | ------- | ------------------ |
| Source    | string     | Yes      | -       | Source entity name |
| Target    | string     | Yes      | -       | Target entity name |
| Min Power | float (kW) | No       | -       | Minimum power flow |
| Max Power | float (kW) | No       | -       | Maximum power flow |

## Net Configuration

| Field | Type   | Required | Default | Description       |
| ----- | ------ | -------- | ------- | ----------------- |
| Name  | string | Yes      | -       | Unique identifier |

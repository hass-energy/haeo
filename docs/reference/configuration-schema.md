# Configuration Schema Reference

Complete configuration schema for all HAEO entities.

## Network Configuration

| Field          | Type            | Required | Default | Description               |
| -------------- | --------------- | -------- | ------- | ------------------------- |
| Name           | string          | Yes      | -       | Unique network identifier |
| Horizon Hours  | integer (1-168) | Yes      | 48      | Optimization time horizon |
| Period Minutes | integer (1-60)  | Yes      | 5       | Time step size            |
| Optimizer      | string          | Yes      | HiGHS   | LP solver to use          |

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

| Field        | Type               | Required | Default | Description           |
| ------------ | ------------------ | -------- | ------- | --------------------- |
| Name         | string             | Yes      | -       | Unique identifier     |
| Import Price | float or sensor(s) | Yes      | -       | Import price (\$/kWh) |
| Export Price | float or sensor(s) | Yes      | -       | Export price (\$/kWh) |
| Import Limit | float (kW)         | No       | -       | Max import power      |
| Export Limit | float (kW)         | No       | -       | Max export power      |

## Photovoltaics Configuration

| Field            | Type           | Required | Default | Description            |
| ---------------- | -------------- | -------- | ------- | ---------------------- |
| Name             | string         | Yes      | -       | Unique identifier      |
| Forecast         | sensor(s)      | Yes      | -       | Solar forecast sensors |
| Production Price | float (\$/kWh) | No       | 0       | Value of generation    |
| Curtailment      | boolean        | No       | false   | Allow curtailment      |

## Load Configuration

### Constant Load

| Field | Type       | Required | Default | Description             |
| ----- | ---------- | -------- | ------- | ----------------------- |
| Name  | string     | Yes      | -       | Unique identifier       |
| Power | float (kW) | Yes      | -       | Fixed power consumption |

### Forecast Load

| Field    | Type      | Required | Default | Description           |
| -------- | --------- | -------- | ------- | --------------------- |
| Name     | string    | Yes      | -       | Unique identifier     |
| Forecast | sensor(s) | Yes      | -       | Load forecast sensors |

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

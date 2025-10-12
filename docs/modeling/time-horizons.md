# Time Horizons and Forecasting

How HAEO discretizes time and uses forecast data.

## Time Discretization

- **Horizon**: Total optimization period (hours)
- **Period**: Time step size (minutes)
- **Steps**: Horizon × 60 / Period

## Rolling Optimization

HAEO re-optimizes periodically, incorporating updated forecasts and current state.

## Forecast Integration

Forecasts provide future values for:

- Electricity prices
- Solar generation
- Load consumption

See [configuration guide](../user-guide/configuration.md) for forecast setup.

# Data Loaders API

Data loader modules for fetching sensor data and forecasts from Home Assistant.

## Loader Types

### ForecastLoader

Loads forecast data from Home Assistant sensors supporting forecast attributes.

Supports:
- Solar forecasts (Open-Meteo, Solcast)
- Price forecasts (Amber Electric, Tibber, Nordpool)
- Load forecasts (custom sensors)

### SensorLoader

Loads current sensor values (battery SOC, current prices).

### ConstantLoader

Loads constant values (fixed prices, fixed loads).

## Location

`custom_components/haeo/data/loader/`

### Key Modules

- `forecast_loader.py`: General forecast loading
- `sensor_loader.py`: Current sensor values
- `constant_loader.py`: Constant values
- `forecast_parsers/`: Format-specific forecast parsers
  - `open_meteo_solar_forecast.py`
  - `solcast_solar.py`
  - `amberelectric.py`
  - `aemo_nem.py`

## Usage

Loaders automatically fetch data during each optimization cycle based on configured sensor entities.

See source code in `custom_components/haeo/data/loader/` for implementation details.

# Coordinator API

The coordinator manages the optimization cycle and data updates.

## HaeoDataUpdateCoordinator

Main coordinator class that:

- Loads data from Home Assistant sensors
- Builds the optimization network model
- Runs the linear programming solver
- Updates result sensors

### Location

`custom_components/haeo/coordinator.py`

### Key Methods

#### `_async_update_data()`

Runs the optimization cycle:

1. Loads current sensor data (battery SOC, prices, forecasts)
2. Builds network model with all configured entities
3. Runs LP solver to find optimal solution
4. Returns results for sensor updates

### Usage

The coordinator is created automatically when the integration is set up. It runs periodically to re-optimize based on updated data.

## Implementation Details

See the source code in `custom_components/haeo/coordinator.py` for full implementation.

!!! tip "Enabling Full API Docs"
    To generate full API documentation with docstrings, set the `ENABLE_MKDOCSTRINGS` environment variable when building docs:
    
    ```bash
    ENABLE_MKDOCSTRINGS=true uv run mkdocs build
    ```

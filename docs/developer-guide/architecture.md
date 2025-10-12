# Architecture

HAEO's architecture follows Home Assistant's integration patterns with specialized optimization components.

## Component Overview

```mermaid
graph TD
    A[Config Flow] --> B[Network Configuration]
    B --> C[Coordinator]
    C --> D[Data Loaders]
    C --> E[Network Model]
    E --> F[LP Solver]
    F --> G[Optimization Results]
    G --> H[Sensors]
```

## Key Components

### Config Flow

User-facing configuration via Home Assistant UI.

Located in: `config_flow.py` and `flows/`

### Coordinator

Manages data updates and optimization cycles.

Located in: `coordinator.py`

### Network Model

Represents the energy system as LP problem.

Located in: `model/`

### Data Loaders

Load forecast and sensor data.

Located in: `data/loader/`

### Sensors

Expose optimization results to Home Assistant.

Located in: `sensors/`

See [API Reference](../api/index.md) for detailed documentation.

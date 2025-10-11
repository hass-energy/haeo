# Config Flow API

Configuration flow handlers for UI-based setup.

## FlowHandler

Main configuration flow class managing:

- Initial network setup
- Entity addition/editing/removal
- Connection management
- Configuration validation

### Location

`custom_components/haeo/config_flow.py` and `custom_components/haeo/flows/`

### Key Components

#### Network Setup

Initial configuration of the optimization network with horizon, period, and solver settings.

#### Options Flow

Handles adding, editing, and removing:
- Batteries
- Grids
- Photovoltaics
- Loads
- Net entities
- Connections

### Usage

Accessed through Home Assistant's UI at **Settings** → **Devices & Services** → **Add Integration** → **HAEO**.

See [Configuration Guide](../user-guide/configuration.md) for user-facing documentation.

## Source Code

See `custom_components/haeo/config_flow.py` and `custom_components/haeo/flows/` for implementation.

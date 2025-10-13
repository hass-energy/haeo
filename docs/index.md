# HAEO - Home Assistant Energy Optimization

Welcome to the HAEO documentation!
HAEO is a Home Assistant custom integration that optimizes your home's energy usage in real-time using linear programming.
It helps you minimize energy costs by intelligently managing battery storage, solar generation, grid import/export, and loads based on electricity prices, forecasts, and system constraints.

## Quick Links

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } __Installation__

    ---

    Get started with HAEO installation via HACS or manual setup.

    [:octicons-arrow-right-24: Installation Guide](user-guide/installation.md)

- :material-cog:{ .lg .middle } __Configuration__

    ---

    Learn how to configure your energy system entities and connections.

    [:octicons-arrow-right-24: Configuration Guide](user-guide/configuration.md)

- :material-function:{ .lg .middle } __Mathematical Modeling__

    ---

    Understand how HAEO models your energy system using linear programming.

    [:octicons-arrow-right-24: Modeling Documentation](modeling/index.md)

- :material-code-braces:{ .lg .middle } __Developer Guide__

    ---

    Contribute to HAEO development or build custom extensions.

    [:octicons-arrow-right-24: Developer Documentation](developer-guide/index.md)

</div>

## What is HAEO?

HAEO stands for **Home Assistant Energy Optimization**. It's a sophisticated integration that:

- **Optimizes energy flow** across all your devices in real-time
- **Minimizes costs** by considering electricity prices and forecasts
- **Manages battery** charging and discharging intelligently
- **Integrates solar** generation with optional curtailment
- **Handles complex systems** with multiple batteries, grids, and loads

## How It Works

```mermaid
flowchart LR
    A[Home Assistant<br/>Sensors] --> B[Data Collection]
    B --> C[Network Model]
    C --> D[Linear Programming<br/>Solver]
    D --> E[Optimal Schedule]
    E --> F[HA Sensors]
    F --> G[Automations &<br/>Dashboards]
```

1. **Collects data** from your Home Assistant sensors (prices, battery SOC, solar forecasts)
2. **Builds a model** representing your energy network with all constraints
3. **Solves optimization** using linear programming to find the lowest-cost solution
4. **Publishes results** as Home Assistant sensors for use in automations

See the [mathematical modeling documentation](modeling/index.md) for detailed information.

## Key Features

### Real-time Optimization

HAEO continuously monitors your energy system and recalculates the optimal strategy as conditions change.
With configurable update intervals and time horizons, you can balance computational load with optimization quality.

### Multiple Device Support

- **Batteries**: Configurable capacity, charge rates, efficiency, and SOC limits
- **Grids**: Import/export with pricing (fixed or forecast-based)
- **Photovoltaics**: Solar generation with optional curtailment capability
- **Loads**: Both constant and forecast-based consumption
- **Net entities**: Virtual nodes for grouping and balancing power flows

### Price-based Strategy

HAEO uses electricity prices (current and forecast) to determine:

- When to charge batteries (during cheap periods)
- When to discharge batteries (during expensive periods)
- Whether to export solar or store it
- How to balance multiple energy sources

### Flexible Constraints

Every device can have constraints:

- Power limits (min/max charge/discharge rates)
- Energy limits (battery capacity, SOC ranges)
- Connection constraints (directional flow limits)

The solver respects all constraints while finding the optimal solution.

## Documentation Structure

### :material-account: User Guide

Perfect for **end users** who want to install and configure HAEO:

- [Installation](user-guide/installation.md) - HACS and manual installation
- [Configuration](user-guide/configuration.md) - Setting up your first network
- [Element Guides](user-guide/elements/index.md) - Detailed configuration for each device type
- [Examples](user-guide/examples/sigenergy-system.md) - Complete system walkthroughs
- [Troubleshooting](user-guide/troubleshooting.md) - Common issues and solutions

### :material-function: Mathematical Modeling

For those interested in **how the optimization works**:

- [Mathematical Modeling Overview](modeling/index.md) - Complete linear programming formulation
- [Battery Model](modeling/battery.md) - Energy storage with SOC dynamics
- [Grid Model](modeling/grid.md) - Import/export with pricing
- [Component Models](modeling/battery.md) - All element mathematical models

### :material-code-braces: Developer Guide

For **contributors and developers**:

- [Architecture](developer-guide/architecture.md) - System design overview
- [Setup](developer-guide/setup.md) - Development environment with `uv`
- [Units](developer-guide/units.md) - Unit system and numerical stability
- [Testing](developer-guide/testing.md) - Running and writing tests
- [Contributing](developer-guide/contributing.md) - Contribution guidelines

### :material-file-document: Reference

Quick **reference tables and schemas**:

- [Entity Types](reference/entities.md) - Complete entity reference
- [Sensor Types](reference/sensors.md) - All sensor types and meanings
- [Configuration Schema](reference/configuration-schema.md) - Full config options
- [LP Solvers](reference/solvers.md) - Supported solvers and setup

## Getting Help

- **Issues**: Report bugs on [GitHub Issues](https://github.com/ha-energy-optimiser/haeo/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/ha-energy-optimiser/haeo/discussions)
- **Contributing**: See our [contribution guidelines](developer-guide/contributing.md)

## Next Steps

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } __New to HAEO?__

    Start with the installation guide to get HAEO up and running.

    [:octicons-arrow-right-24: Install HAEO](user-guide/installation.md)

- :material-book-open-variant:{ .lg .middle } __Want to understand the math?__

    Explore the mathematical modeling documentation.

    [:octicons-arrow-right-24: Mathematical Models](modeling/index.md)

- :material-code-tags:{ .lg .middle } __Want to contribute?__

    Check out the developer guide and contribution workflow.

    [:octicons-arrow-right-24: Developer Guide](developer-guide/index.md)

</div>

<p align="center">
    <img src="assets/logo.svg" alt="HAEO Logo" width="512">
</p>

# HAEO - Home Assistant Energy Optimization

Welcome to the HAEO documentation!
HAEO is a Home Assistant custom integration that optimizes your home's energy usage in real-time using linear programming.
It helps you minimize energy costs by intelligently managing battery storage, solar generation, grid import/export, and loads based on electricity prices, forecasts, and system constraints.

## Quick Links

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } __Installation__

    Get started with HAEO installation via HACS or manual setup.

    [:material-arrow-right: Installation Guide](user-guide/installation.md)

- :material-cog:{ .lg .middle } __Configuration__

    Learn how to configure your energy system elements and connections.

    [:material-arrow-right: Configuration Guide](user-guide/configuration.md)

- :material-function:{ .lg .middle } __Mathematical Modeling__

    Understand how HAEO models your energy system using linear programming.

    [:material-arrow-right: Modeling Documentation](modeling/index.md)

- :material-code-braces:{ .lg .middle } __Developer Guide__

    Contribute to HAEO development or build custom extensions.

    [:material-arrow-right: Developer Documentation](developer-guide/index.md)

</div>

## What is HAEO?

HAEO continuously evaluates forecasts, device limits, and prices to produce an optimal plan for your configured elements.
It works alongside other Home Assistant integrations that provide sensor data, and exposes its results as sensors you can reference in automations or dashboards.

## Key Features

### Optimization that follows your data

HAEO watches the sensors you configure and re-optimizes whenever inputs change.
You choose the horizon and resolution through the UI to balance responsiveness with complexity.
See the [configuration guide](user-guide/configuration.md#horizon-hours) for advice on selecting a horizon window.

### Built for the Home Assistant ecosystem

Configuration uses the standard [Home Assistant integration flow](https://www.home-assistant.io/integrations/#configuring-integrations) and all results appear as sensors, so there is no separate management interface.

### Works with diverse energy setups

Whether you have storage, on-site generation, flexible loads, or only the grid, HAEO treats each component as an element in the same optimization network.

### Extensible modeling

The modeling documentation explains how HAEO formulates the linear program, and the developer guide shows how to extend it when new element types are needed.

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

- [Mathematical Modeling Overview](modeling/index.md) - Linear programming formulation and network structure
- [Battery Model](modeling/battery.md) - Storage dynamics and constraints
- [Grid Model](modeling/grid.md) - Import and export cost modeling
- [Component Models](modeling/battery.md) - Element-by-element formulations

### :material-code-braces: Developer Guide

For **contributors and developers**:

- [Architecture](developer-guide/architecture.md) - System design overview
- [Setup](developer-guide/setup.md) - Development environment with `uv`
- [Units](developer-guide/units.md) - Unit system and numerical stability
- [Testing](developer-guide/testing.md) - Running and writing tests
- [Contributing](developer-guide/contributing.md) - Contribution guidelines

### :material-file-document: Reference

Quick **reference tables and schemas**:

- [Element Types](reference/elements.md) - Complete element reference
- [Sensor Types](reference/sensors.md) - All sensor types and meanings
- [Configuration Schema](reference/configuration-schema.md) - Full config options

## Getting Help

- **Issues**: Report bugs on [GitHub Issues](https://github.com/hass-energy/haeo/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/hass-energy/haeo/discussions)
- **Contributing**: See our [contribution guidelines](developer-guide/contributing.md)

## Next Steps

<div class="grid cards" markdown>

- :material-rocket-launch:{ .lg .middle } __New to HAEO?__

    Start with the installation guide to get HAEO up and running.

    [:material-arrow-right: Install HAEO](user-guide/installation.md)

- :material-book-open-variant:{ .lg .middle } __Want to understand the math?__

    Explore the mathematical modeling documentation.

    [:material-arrow-right: Mathematical Models](modeling/index.md)

- :material-code-tags:{ .lg .middle } __Want to contribute?__

    Check out the developer guide and contribution workflow.

    [:material-arrow-right: Developer Guide](developer-guide/index.md)

</div>

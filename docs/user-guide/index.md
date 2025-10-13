# User Guide

Welcome to the HAEO User Guide!
This section will help you install, configure, and use HAEO to optimize your home's energy usage.

## What You'll Learn

This guide covers everything you need to know as an end user:

1. **[Installation](installation.md)** - Install HAEO via HACS or manually
2. **[Configuration](configuration.md)** - Set up your first energy network
3. **[Elements](elements/index.md)** - Configure batteries, grids, solar, and loads
4. **[Connections](elements/connections.md)** - Define how energy flows between devices
5. **[Understanding Results](optimization.md)** - Interpret optimization outputs
6. **[Examples](examples/sigenergy-system.md)** - Complete system configuration walkthroughs
7. **[Troubleshooting](troubleshooting.md)** - Solve common issues

## Prerequisites

Before installing HAEO, ensure you have:

- **Home Assistant** 2025.4.4 or newer
- **HACS** installed (for HACS installation method)
- **Sensors** for:
    - Battery state of charge (if using batteries)
    - Electricity prices (current or forecast)
    - Solar forecast (if using solar)
    - Load forecast (if optimizing loads)

!!! tip "Forecast Sensors"

    Many integrations provide forecast data that HAEO can use:

    - **Electricity prices**: Amber Electric, Nordpool, Tibber
    - **Solar forecast**: [Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast), Solcast
    - **Load forecast**: Custom sensors based on your usage patterns

## Quick Start Path

The typical workflow for setting up HAEO is:

1. Install HAEO via HACS or manually
2. Create a network through the UI
3. Add a battery (if you have one)
4. Add a grid connection
5. Add solar panels or loads
6. Define connections between components
7. View optimization results in sensors
8. Create automations based on the optimal schedule

## Project Philosophy

HAEO follows a focused, Unix-like philosophy: **do one thing well**.

### What HAEO Does

HAEO focuses exclusively on **energy optimization**.
It computes the optimal schedule for your batteries, loads, and other devices based on forecasts and constraints.

### What HAEO Doesn't Do

HAEO intentionally does not include:

- **Solar forecasting** - Use Open-Meteo, Solcast, or other specialized integrations
- **Price fetching** - Use Amber, Nordpool, Tibber, or other provider integrations
- **Device control** - Use Home Assistant automations to implement the optimal schedule
- **Load forecasting** - Use existing integrations or template sensors

### Why This Approach?

This focused design means:

- **Better integration**: Works seamlessly with the existing Home Assistant ecosystem
- **Flexibility**: Choose the best-in-class solution for each component
- **Maintainability**: Simpler codebase focused on optimization algorithms
- **Reliability**: Fewer moving parts and external dependencies

HAEO provides optimization results as sensors with forecast attributes, letting you build automations with the full power of Home Assistant.

## Installation Methods

We recommend installing via HACS for automatic updates, but manual installation is also supported.

[:octicons-arrow-right-24: Continue to Installation](installation.md)

## Example Systems

Not sure where to start? Check out our complete system examples:

- **[Sigenergy System](examples/sigenergy-system.md)** - Battery, solar, grid, and forecast load

These examples show real-world configurations with all the details you need to replicate similar setups.

## Getting Help

If you run into issues:

1. Check the **[Troubleshooting](troubleshooting.md)** page for common problems
2. Search existing [GitHub Issues](https://github.com/ha-energy-optimiser/haeo/issues)
3. Ask in [GitHub Discussions](https://github.com/ha-energy-optimiser/haeo/discussions)
4. Report bugs by opening a new issue

!!! warning "Important"

    Always include your Home Assistant version, HAEO version, and relevant configuration (with sensitive data removed) when asking for help.

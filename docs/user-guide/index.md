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

Before installing HAEO, confirm:

- Your Home Assistant core version is 2025.4.4 or newer
- You can add integrations through the UI or [HACS](https://hacs.xyz/) if you prefer managed updates
- The data you plan to optimize (prices, forecasts, sensor readings) is already available in Home Assistant or will be added with other integrations

## Quick start path

The typical workflow for setting up HAEO is:

1. Install HAEO via HACS or manually
2. Create a network through the UI
3. Add the elements that reflect your devices
4. Define connections between elements
5. View optimization results in sensors and build automations around them

!!! tip "Troubleshooting and Support"

    If you encounter issues, HAEO provides diagnostic information you can export for troubleshooting or when requesting help.
    See the [troubleshooting guide](troubleshooting.md) for details on accessing diagnostic data.

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
- **Load forecasting** - Use [HAFO](https://hafo.haeo.io), existing integrations, or template sensors

### Why This Approach?

This focused design means:

- **Better integration**: Works seamlessly with the existing Home Assistant ecosystem
- **Flexibility**: Choose the best-in-class solution for each component
- **Maintainability**: Simpler codebase focused on optimization algorithms
- **Reliability**: Fewer moving parts and external dependencies

HAEO provides optimization results as sensors with forecast attributes, letting you build automations with the full power of Home Assistant.

## Installation Methods

We recommend installing via HACS for automatic updates, but manual installation is also supported.

[:material-arrow-right: Continue to Installation](installation.md)

## Example Systems

Not sure where to start? Check out our complete system examples:

- **[Sigenergy System](examples/sigenergy-system.md)** - Battery, solar, grid, and forecast load

These examples show real-world configurations with all the details you need to replicate similar setups.

## Getting Help

If you run into issues:

1. Check the **[Troubleshooting](troubleshooting.md)** page for common problems
2. Search existing [GitHub Issues](https://github.com/hass-energy/haeo/issues)
3. Ask in [GitHub Discussions](https://github.com/hass-energy/haeo/discussions)
4. Report bugs by opening a new issue

!!! warning "Important"

    Always include your Home Assistant version, HAEO version, and relevant configuration (with sensitive data removed) when asking for help.

## Next Steps

Continue with these guides to get HAEO running smoothly in your environment.

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } __Install HAEO__

    Start the integration in Home Assistant via HACS or manual setup.

    [:material-arrow-right: Installation guide](installation.md)

- :material-cog-outline:{ .lg .middle } __Configure your first network__

    Add elements and connections so HAEO can optimize your system.

    [:material-arrow-right: Configuration guide](configuration.md)

- :material-wrench:{ .lg .middle } __Troubleshooting guidance__

    Fix common setup issues and keep the optimizer running smoothly.

    [:material-arrow-right: Troubleshooting tips](troubleshooting.md)

</div>

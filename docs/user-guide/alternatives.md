# HAEO vs EMHASS

When exploring energy optimization solutions for Home Assistant, you'll likely encounter two actively maintained projects: HAEO and EMHASS.
Both aim to optimize home energy usage but take fundamentally different architectural approaches.
This page provides a fair, technical comparison to help you choose the solution that best fits your needs.

## Quick comparison

| Feature                  | HAEO                          | EMHASS                                     |
| ------------------------ | ----------------------------- | ------------------------------------------ |
| **Type**                 | Native integration            | Add-on                                     |
| **Maintenance**          | Active                        | Active                                     |
| **Installation**         | HACS → Integration            | Add-on store                               |
| **HA requirements**      | Any installation method       | Home Assistant OS or Supervised            |
| **Configuration**        | UI-based                      | Web UI + Configuration files               |
| **Network topology**     | Flexible graph                | Fixed structure                            |
| **Optimization**         | Linear programming (LP)       | Mixed integer linear programming (MILP)    |
| **Forecasting**          | Via other HA integrations     | Built-in ML and solar forecasting          |
| **Primary use case**     | Battery/solar optimization    | Appliance scheduling + battery/solar       |
| **Multi-element support** | Multiple batteries/arrays/grids | Limited                                   |
| **Integration method**   | Native HA sensors             | Sensors + REST API + shell commands        |

## Philosophical differences

The core difference between HAEO and EMHASS reflects their origins and design philosophies:

**EMHASS** (developed by an electrical engineer) takes an integrated approach: it's purpose-built for energy management with forecasting, machine learning, and discrete load scheduling all included.
It assumes a more standard system topology and provides comprehensive features in a single package.

**HAEO** (developed by a software engineer) follows the Unix philosophy: do one thing well.
It focuses purely on optimization with a flexible, graph-based network model, relying on other Home Assistant integrations to provide forecasting data.
The flexibility to model any network topology through connections is its defining characteristic.

You might think of it as: an electrical engineer building a software project versus a software engineer building an electrical project.

## EMHASS

[GitHub](https://github.com/davidusb-geek/emhass) • [Documentation](https://emhass.readthedocs.io/) • [Community discussion](https://community.home-assistant.io/t/emhass-an-energy-management-for-home-assistant/338126)

**Status**: Actively maintained, mature project with established community

### Overview

EMHASS (Energy Management for Home Assistant) is a Python-based add-on that optimizes home energy management through day-ahead optimization.
It excels at scheduling deferrable loads (washing machines, dishwashers, EV chargers, pool pumps) to minimize costs and maximize self-consumption of solar energy.

### Strengths

- **Mixed integer linear programming**: Can handle discrete decisions (on/off appliances), enabling true appliance scheduling optimization
- **Built-in forecasting**: Includes machine learning-based load forecasting and integrates with solar forecasting services (Solcast, Forecast.Solar)
- **Purpose-built for deferrable loads**: Designed specifically for appliance scheduling and load management
- **Mature and proven**: Established project with large community, extensive real-world deployments, and comprehensive documentation
- **Separate machine capability**: Can run on a different machine than Home Assistant, beneficial for resource-constrained systems
- **Simple installation**: Direct installation from Home Assistant add-on store
- **Thermal load support**: Can model and optimize thermal loads (hot water heaters, etc.)

### Limitations

- **Requires HA OS/Supervised**: Add-on limitation means it won't work with Container or Core installations
- **Fixed network topology**: Less flexible for modeling custom or complex system architectures
- **Configuration complexity**: Despite simpler architecture, configuration can be complex and requires understanding many parameters
- **Limited multi-element support**: Harder to model multiple batteries, arrays, or custom grid configurations
- **Integration overhead**: Uses combination of sensors, REST API, and shell commands rather than native integration

### Best for

- Users needing discrete appliance/load scheduling
- Those wanting built-in ML and solar forecasting
- Home Assistant OS or Supervised installations
- Standard solar + battery + grid setups
- Resource-constrained HA instances (can offload to separate machine)
- Users preferring add-on installation model
- Systems with thermal loads

## HAEO

[GitHub](https://github.com/hass-energy/haeo) • [Documentation](../index.md) • [GitHub discussions](https://github.com/hass-energy/haeo/discussions)

**Status**: Actively maintained, newer project

### Overview

HAEO (Home Assistant Energy Optimization) is a native Home Assistant integration that optimizes energy networks through flexible topology modeling.
Its key innovation is the ability to model any network structure through connections between elements, enabling custom system configurations that emerge from the graph structure itself.

### Strengths

- **Flexible network topology**: Model any system structure through connections - the strongest differentiator. Graph-based approach enables emergent behavior for complex systems
- **Native Home Assistant integration**: Works with any HA installation method (OS, Supervised, Container, Core)
- **Full UI configuration**: Everything configurable through Home Assistant's UI with organized devices
- **Multiple element support**: Easy support for multiple batteries, solar arrays, grids, and loads
- **Modern codebase**: Python 3.13+, platinum-level code quality standards, strong typing, comprehensive testing
- **Lower latency**: Runs alongside Home Assistant instance for minimal delay
- **Native sensor integration**: Sensors organized into devices, persist between reboots, leverage native HA features
- **Unique features**: Battery overcharge/undercharge protection, modeling of non-electric energy systems (hot water via connections)
- **Extensibility**: Graph structure allows modeling diverse energy systems without code changes

### Limitations

- **Continuous optimization only**: Linear programming (no MILP yet), so cannot optimize discrete appliance scheduling
- **Graph complexity**: Requires understanding topology and connection concepts, which adds initial learning curve
- **Newer project**: Smaller community, less proven track record compared to EMHASS
- **Requires HACS**: Additional step before installation (though HACS is very common)
- **Setup complexity**: Flexibility means more configuration options and decisions
- **External forecasting dependency**: Relies entirely on other HA integrations for forecast data
- **Missing features**: Does not yet have thermal loads or deferrable load scheduling (planned future additions)

### Best for

- Complex or custom system topologies
- Users with multiple batteries, arrays, or grids
- Home Assistant Container or Core installations
- Those preferring native HA integration
- Users valuing UI-based configuration
- Systems needing modeling flexibility (AC/DC splits, hybrid inverters, multiple meters)
- Users who prioritize modern code quality and software architecture
- Specific feature needs like battery overcharge protection

## Technical comparison

### Network modeling

| Feature                     | HAEO                           | EMHASS         |
| --------------------------- | ------------------------------ | -------------- |
| Multiple batteries          | Yes (unlimited)                | Limited        |
| Multiple solar arrays       | Yes (unlimited)                | Limited        |
| Custom topology             | Flexible graph                 | Fixed          |
| Hybrid inverters            | Via connection configuration   | Via config     |
| Multiple grids              | Yes                            | No             |
| Non-electric energy systems | Yes (via connections)          | Thermal loads  |
| AC/DC network splits        | Yes (via connections)          | No             |

### Optimization

| Feature            | HAEO                    | EMHASS                |
| ------------------ | ----------------------- | --------------------- |
| Algorithm          | Linear programming (LP) | Mixed integer LP      |
| Solver             | HiGHS                   | Configurable          |
| Discrete decisions | No (continuous only)    | Yes (on/off control)  |
| Time horizon       | Configurable            | Configurable          |
| Time resolution    | Configurable (1-60 min) | Configurable          |
| Battery management | Charge/discharge rates  | Charge/discharge      |
| Overcharge/undercharge protection | Yes         | No                    |

### Integration and setup

| Feature              | HAEO                                    | EMHASS                              |
| -------------------- | --------------------------------------- | ----------------------------------- |
| Installation method  | HACS → Integration                      | Add-on store                        |
| HA compatibility     | All (OS, Supervised, Container, Core)   | OS and Supervised only              |
| Configuration        | Full UI-based                           | Web UI + YAML files                 |
| Learning curve       | Moderate (graph/topology concepts)      | Moderate (many config parameters)   |
| Setup complexity     | High flexibility = more decisions       | Simpler architecture, complex config |
| Documentation        | Growing                                 | Extensive, mature                   |
| Community size       | Smaller (newer)                         | Larger (established)                |

### Features

| Feature                | HAEO                           | EMHASS                              |
| ---------------------- | ------------------------------ | ----------------------------------- |
| Forecasting            | Via HA integrations (modular)  | Built-in ML + solar forecasting     |
| Sensor integration     | Native HA devices and sensors  | Published sensors + REST API        |
| Deferrable loads       | Not yet (planned)              | Yes (core feature)                  |
| Thermal loads          | Via connections (experimental) | Yes (built-in)                      |
| Appliance scheduling   | Not yet (planned)              | Yes (MILP-based)                    |
| Battery optimization   | Yes (core feature)             | Yes (core feature)                  |
| Solar optimization     | Yes (core feature)             | Yes (core feature)                  |
| Control method         | HA automations with sensors    | Shell commands, REST, sensors       |

## When to choose each solution

### Choose EMHASS if you

- Need discrete appliance or load scheduling (washing machine, EV charger timing)
- Want built-in machine learning and solar forecasting without installing separate integrations
- Prefer add-on installation model
- Have a standard solar + battery + grid setup
- Need to run optimization on a separate machine (resource-constrained HA)
- Want an established project with proven track record and large community
- Need thermal load optimization
- Are running Home Assistant OS or Supervised

### Choose HAEO if you

- Have a complex or custom system topology that doesn't fit standard patterns
- Need to model multiple batteries, solar arrays, or grid connections
- Are running Home Assistant Container or Core (where add-ons aren't available)
- Prefer native Home Assistant integration with lower latency
- Want UI-based configuration for all settings
- Value modern codebase with strong typing and comprehensive testing
- Need specific features like battery overcharge/undercharge protection
- Want to model non-standard systems (AC/DC splits, multiple meters, custom connections)
- Prioritize software quality and maintainability

## Can you use both?

Technically, yes.
They have overlapping capabilities but could be complementary:

- **HAEO** for battery and solar optimization with flexible topology
- **EMHASS** for discrete appliance scheduling

However, in practice, most users will choose one or the other since both handle battery and solar optimization, which creates redundancy.
The overlap is significant enough that running both adds complexity without major benefit for most systems.

## Making your choice

Consider these factors:

1. **System complexity**: Simple standard setup → either works; complex topology → HAEO
2. **Installation method**: HA OS/Supervised → either works; Container/Core → HAEO only
3. **Optimization type**: Appliance scheduling → EMHASS; battery/solar only → either works
4. **Configuration preference**: UI-based → HAEO; file-based acceptable → EMHASS
5. **Forecasting**: Want built-in → EMHASS; happy using other integrations → HAEO
6. **Project maturity**: Want established → EMHASS; modern codebase → HAEO
7. **Resource constraints**: Need separate machine → EMHASS; prefer integrated → HAEO

## Getting help

### HAEO support

- [GitHub issues](https://github.com/hass-energy/haeo/issues) - Bug reports and feature requests
- [GitHub discussions](https://github.com/hass-energy/haeo/discussions) - Questions and community support
- [Documentation](../index.md) - Comprehensive guides

### EMHASS support

- [GitHub repository](https://github.com/davidusb-geek/emhass) - Code and issues
- [Documentation](https://emhass.readthedocs.io/) - Setup and configuration guides
- [Community forum](https://community.home-assistant.io/t/emhass-an-energy-management-for-home-assistant/338126) - Active discussion thread

## Conclusion

Both HAEO and EMHASS are actively maintained, quality projects that solve real energy optimization problems for Home Assistant users.
They represent different architectural philosophies:

- **EMHASS**: Integrated solution with rigid structure, built-in forecasting, and discrete optimization capabilities
- **HAEO**: Modular solution with flexible structure, external forecasting, and continuous optimization focus

Neither is objectively "better" - the right choice depends on your specific system, installation method, optimization needs, and preferences.
EMHASS excels at appliance scheduling with its MILP solver and offers a comprehensive, proven solution.
HAEO excels at flexible topology modeling and native integration with modern code quality.

Choose based on what matters most for your use case: discrete control and built-in forecasting (EMHASS), or flexible topology and native integration (HAEO).

## Next steps

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Install HAEO**

    ---

    Get started with HAEO by installing it through HACS and setting up your first energy network.

    [:material-arrow-right: Installation guide](installation.md)

-   :material-connection:{ .lg .middle } **Understand forecasting**

    ---

    Learn how HAEO uses forecast data from Home Assistant sensors to optimize your energy system.

    [:material-arrow-right: Forecasts and sensors](forecasts-and-sensors.md)

-   :material-frequently-asked-questions:{ .lg .middle } **Common questions**

    ---

    Find answers to frequently asked questions about HAEO's capabilities and use cases.

    [:material-arrow-right: FAQ](faq.md)

-   :material-github:{ .lg .middle } **Join the community**

    ---

    Connect with other HAEO users, ask questions, and share your experiences.

    [:material-arrow-right: GitHub discussions](https://github.com/hass-energy/haeo/discussions)

</div>

# HAEO vs Alternatives

If you're considering energy optimization solutions for Home Assistant, you may have encountered other projects.
This page compares HAEO with alternatives to help you make an informed choice.

## Quick Comparison

| Feature              | HAEO               | WattWise            | EMHASS                             |
| -------------------- | ------------------ | ------------------- | ---------------------------------- |
| **Type**             | Native Integration | AppDaemon App       | Add-on                             |
| **Maintenance**      | Active             | Unmaintained        | Active                             |
| **Configuration**    | UI-based           | Configuration files | Configuration files + UI           |
| **Flexibility**      | High               | Medium              | Low                                |
| **Dependencies**     | None (native HA)   | AppDaemon           | Docker add-on                      |
| **Network Topology** | Flexible graph     | Fixed structure     | Fixed structure                    |
| **Optimization**     | Linear Programming | Linear Programming  | Mixed Integer Linear Programming   |
| **Integration**      | Native HA sensors  | Sensor publishing   | Sensor publishing + shell commands |

## HAEO

**Home Assistant Energy Optimization**

### Strengths

- ✅ **Native Integration**: Full Home Assistant integration
- ✅ **UI Configuration**: Everything configurable through HA's UI
- ✅ **Flexible Topology**: Model any network structure with connections
- ✅ **Active Development**: Regular updates and bug fixes
- ✅ **Modern Codebase**: Python 3.13+, type-safe, well-tested
- ✅ **Extensible**: Easy to add new element types
- ✅ **Sensors**: Rich sensor data with forecast attributes
- ✅ **Multiple Elements**: Support for multiple batteries, grids, loads, etc.

### Best For

- Users who want native HA integration
- Complex systems with custom topologies
- Users comfortable with UI configuration
- Systems requiring multiple batteries or arrays
- Users who value active maintenance

### Installation

Via HACS as a custom integration.

## WattWise

[GitHub](https://github.com/bullitt186/ha-wattwise/) • [Community Discussion](https://community.home-assistant.io/t/wattwise-energy-forecasting-and-battery-control-for-dynamic-energy-tariffs-like-tibber/790613)

### Overview

WattWise is an AppDaemon-based energy management system for Home Assistant.

### Status

⚠️ **No longer actively maintained** - Last significant update was over a year ago.

### Strengths

- ✅ AppDaemon-based (if you already use AppDaemon)
- ✅ Designed for Tibber integration
- ✅ Simpler for basic setups

### Limitations

- ❌ **Unmaintained**: No active development or bug fixes
- ❌ **AppDaemon Dependency**: Requires AppDaemon installation and maintenance
- ❌ **Fixed Structure**: Less flexible than HAEO for custom topologies
- ❌ **Configuration**: File-based configuration only
- ❌ **Limited Documentation**: Harder to get started

### Best For

- Users already running AppDaemon
- Simple Tibber-based setups
- Users comfortable with legacy software

### Migration to HAEO

If you're using WattWise, migrating to HAEO offers:

- Active maintenance and bug fixes
- More flexible system modeling
- UI-based configuration
- Better integration with Home Assistant

## EMHASS

[GitHub](https://github.com/davidusb-geek/emhass) • [Community Discussion](https://community.home-assistant.io/t/emhass-an-energy-management-for-home-assistant/338126)

### Overview

EMHASS (Energy Management for Home Assistant) is a Docker add-on for Home Assistant.

### Status

✅ **Actively maintained**

### Strengths

- ✅ **Actively Developed**: Regular updates
- ✅ **Mature Project**: Well-established in community
- ✅ **Web UI**: Configuration through web interface
- ✅ **Mixed Integer LP**: Can handle discrete decisions

### Limitations

- ❌ **Add-on Only**: Requires Home Assistant OS or Supervised
- ❌ **Rigid Configuration**: Less flexible than HAEO
- ❌ **Fixed Topology**: Predefined system structure
- ❌ **Complex Setup**: Configuration can be challenging
- ❌ **Limited Multi-Element Support**: Harder to model multiple batteries/arrays
- ❌ **External Integration**: Shell commands and REST calls vs native sensors

### Best For

- Home Assistant OS/Supervised users
- Standard solar + battery + grid setups
- Users wanting discrete optimization (e.g., appliance scheduling)
- Users comfortable with add-on management

### HAEO vs EMHASS

**Choose HAEO if you want**:

- Native Home Assistant integration
- Flexible system topology (multiple batteries, complex connections)
- UI-based element configuration
- Custom network structures (AC/DC splits, multiple meters)
- Pure Python implementation

**Choose EMHASS if you want**:

- Add-on installation model
- Mixed integer optimization for discrete decisions
- Established project with large community
- You're already using EMHASS-compatible hardware

## Feature Comparison

### Network Modeling

| Feature               | HAEO               | WattWise   | EMHASS        |
| --------------------- | ------------------ | ---------- | ------------- |
| Multiple Batteries    | ✅ Yes             | ⚠️ Limited | ⚠️ Limited    |
| Multiple Solar Arrays | ✅ Yes             | ⚠️ Limited | ⚠️ Limited    |
| Custom Topology       | ✅ Flexible graph  | ❌ Fixed   | ❌ Fixed      |
| Hybrid Inverters      | ✅ Via connections | ❌ Limited | ⚠️ Via config |
| Multiple Grids        | ✅ Yes             | ❌ No      | ❌ No         |

### Optimization

| Feature            | HAEO                    | WattWise           | EMHASS           |
| ------------------ | ----------------------- | ------------------ | ---------------- |
| Algorithm          | Linear Programming      | Linear Programming | Mixed Integer LP |
| Solver             | HiGHS                   | Solver-dependent   | Solver-dependent |
| Time Horizon       | Configurable            | Fixed              | Configurable     |
| Time Resolution    | Configurable (1-60 min) | Fixed              | Configurable     |
| Discrete Decisions | ❌ Continuous only      | ❌ Continuous only | ✅ Yes           |

### Integration

| Feature       | HAEO              | WattWise          | EMHASS            |
| ------------- | ----------------- | ----------------- | ----------------- |
| Installation  | HACS Integration  | AppDaemon         | Docker Add-on     |
| Configuration | HA UI             | YAML files        | Web UI + YAML     |
| Sensors       | Native HA sensors | Published sensors | Published sensors |
| Forecast Data | Sensor attributes | Sensor attributes | REST API          |
| Control       | HA automations    | AppDaemon         | Shell commands    |

## When to Choose HAEO

Choose HAEO if you:

- ✅ Want a native Home Assistant integration
- ✅ Have or need a flexible network topology
- ✅ Prefer UI configuration over YAML
- ✅ Value active maintenance
- ✅ Want to use existing HA integrations
- ✅ Need multiple batteries or arrays
- ✅ Have a custom or complex setup

### When to Choose Alternatives

Consider alternatives if you:

- Need discrete optimization (appliance scheduling) → EMHASS
- Already use AppDaemon heavily → WattWise (though consider migration)
- Prefer add-on installation model → EMHASS
- Have a very simple, standard setup → Any option works

## Migration Guides

### From WattWise to HAEO

1. Install HAEO via HACS
2. Create network in HAEO UI
3. Add elements (battery, grid, solar, loads)
4. Define connections
5. Map WattWise sensors to HAEO equivalents
6. Update automations to use HAEO sensors
7. Test optimization
8. Disable WattWise

### From EMHASS to HAEO

1. Document your EMHASS configuration
2. Install HAEO via HACS
3. Create equivalent network in HAEO
4. Add elements matching your EMHASS setup
5. Define connections between elements
6. Update automations to use HAEO sensors
7. Run both in parallel initially
8. Verify HAEO optimization matches expectations
9. Disable EMHASS

## Contributing

All three projects welcome contributions:

- **HAEO**: [Contributing Guide](../developer-guide/contributing.md)
- **WattWise**: See GitHub repository (note: unmaintained)
- **EMHASS**: See GitHub repository

## Getting Help

### HAEO Support

- [GitHub Issues](https://github.com/hass-energy/haeo/issues)
- [GitHub Discussions](https://github.com/hass-energy/haeo/discussions)
- [Documentation](../index.md)

### Community Forums

- [WattWise Community Thread](https://community.home-assistant.io/t/wattwise-energy-forecasting-and-battery-control-for-dynamic-energy-tariffs-like-tibber/790613)
- [EMHASS Community Thread](https://community.home-assistant.io/t/emhass-an-energy-management-for-home-assistant/338126)

## Conclusion

All three projects aim to optimize home energy usage, but take different approaches:

- **HAEO**: Native integration, flexible, UI-configured, actively maintained
- **WattWise**: AppDaemon-based, simpler, unmaintained
- **EMHASS**: Add-on, established, discrete optimization capable

Choose based on your:

- Installation preferences (native vs AppDaemon vs add-on)
- System complexity
- Configuration preferences (UI vs files)
- Need for active maintenance
- Optimization requirements

For most users wanting a flexible, actively maintained solution with native Home Assistant integration, **HAEO is the recommended choice**.

[:material-arrow-right: Get Started with HAEO](installation.md)

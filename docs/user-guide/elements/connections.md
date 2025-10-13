# Connections

Connections define how power flows between elements in your network.

## Overview

A connection represents a power flow path from a source element to a target element, with optional power limits.

## Configuration

### Source

The element where power comes from.

### Target

The element where power goes to.

### Min Power (Optional)

Minimum power flow (kW). Can be negative for bidirectional flow.

### Max Power (Optional)

Maximum power flow (kW).

## Examples

### Bidirectional Connection

Grid ↔ Battery:

```yaml
Source: Grid
Target: Battery
Min Power: -10 kW # Can flow either direction
Max Power: 10 kW
```

### Unidirectional Connection

Solar → Net:

```yaml
Source: Solar
Target: Net
Min Power: 0 kW # One-way only
Max Power: None # Unlimited
```

## Network Topology

```mermaid
graph LR
    Grid[Grid] <-->|±10kW| Net[Net]
    Battery[Battery] <-->|±5kW| Net
    Solar[Solar] -->|→| Net
    Net -->|→| Load[Load]
```

## Troubleshooting

See [troubleshooting guide](../troubleshooting.md#graph-isnt-connected-properly) for connection issues.

## Modeling Hybrid Inverters {#hybrid-inverters}

Hybrid inverters (AC-DC converters) can be modeled as connections between net elements:

```mermaid
graph LR
    subgraph DC Side
        Battery[Battery] --> DC_Net[DC Net]
        Solar[Solar] --> DC_Net
    end

    subgraph AC Side
        Grid[Grid] <--> AC_Net[AC Net]
        AC_Net --> Load[Load]
    end

    DC_Net <-->|Inverter<br/>Connection| AC_Net
```

### Configuration

Create two net elements (DC and AC) and connect them with power limits:

```yaml
Source: DC Net
Target: AC Net
Min Power: -5 kW # 5kW charging (AC→DC)
Max Power: 5 kW # 5kW discharging (DC→AC)
```

The connection limits represent the inverter's power rating.

!!! tip "Power Limits: Elements vs Connections"

    - **Element limits** (battery charge/discharge rates) represent device capabilities.
    - **Connection limits** (inverter ratings) represent power flow constraints.

    Both are respected during optimization.

## Related Documentation

- [Connection Modeling](../../modeling/connections.md)
- [Net Element Modeling](../../modeling/net-entity.md)

[:octicons-arrow-right-24: Continue to Understanding Results](../optimization.md)

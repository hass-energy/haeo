# Net Entity Configuration

Virtual balance points enforcing power conservation (Kirchhoff's law).

## Configuration Fields

| Field    | Type   | Required | Default | Description       |
| -------- | ------ | -------- | ------- | ----------------- |
| **Name** | String | Yes      | -       | Unique identifier |
| **Type** | "Net"  | Yes      | -       | Entity type       |

## Name

Descriptive of electrical location: "Main Net", "AC Panel", "DC Bus", "Home Circuit"

## Purpose

Nets are connection hubs where power balance is enforced:

$$
\text{Power In} = \text{Power Out}
$$

Not physical devices - represent electrical junctions.

## Use Cases

**Single net (simple)**: Central hub for all entities.

```mermaid
graph LR
    Grid<-->Net
    Solar-->Net
    Battery<-->Net
    Net-->Load

    style Net fill:#90EE90
```

Most residential systems use one net.

**Multiple nets (complex)**: Separate AC/DC or hierarchical distribution.

```mermaid
graph LR
    Solar-->DC[DC Net]
    Battery<-->DC
    DC<-->|Inverter|AC[AC Net]
    Grid<-->AC
    AC-->Load

    style DC fill:#E1F5FF
    style AC fill:#FFF5E1
```

Hybrid inverter systems with separate buses.

## Configuration Example

```yaml
Name: Main Net
Type: Net
```

Then connect entities to "Main Net" via connections.

## No Sensors Created

Nets are virtual - no physical measurements. Monitor connected entity sensors instead.

## Troubleshooting

**Infeasible optimization**: Check all entities connected, sufficient sources exist, connection directions correct, limits not too restrictive.

**Unexpected power flows**: Verify connection endpoints, review net names unique, check connection min/max power limits.

## Multiple Nets

**Use when**:

- Physical separation (AC/DC)
- Intermediate limits (inverter, feeder capacity)
- Hierarchical distribution

**Configuration**: Create multiple net entities, link with connections (e.g., inverter between DC and AC nets).

**Complexity**: More configuration, more constraints, but models real architecture accurately.

## Hybrid Inverter Modeling

For hybrid (AC/DC) inverter systems, use separate AC and DC nets with a connection between them:

```mermaid
graph LR
    subgraph DC Side
        Battery[Battery] <--> DC_Net[DC Net]
        Solar[Solar] --> DC_Net
    end

    subgraph AC Side
        Grid[Grid] <--> AC_Net[AC Net]
        AC_Net --> Load[Load]
    end

    DC_Net <-->|Inverter<br/>Connection| AC_Net
```

The **connection** between DC and AC nets represents the inverter.
Set connection power limits to match the inverter rating.

See [Connections](connections.md) for configuring the inverter connection.

## Related Documentation

- [Net Entity Modeling](../../modeling/net-entity.md)
- [Mathematical Modeling](../../modeling/index.md)
- [Connections Guide](connections.md)

[:octicons-arrow-right-24: Continue to Connections Guide](connections.md)

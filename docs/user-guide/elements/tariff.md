# Tariff

A **Tariff** adds per-kWh pricing to specific power flows based on where the power originates and where it's consumed.

## How It Works

HAEO tracks power provenance using tags — each source device produces power on its own tag (like a VLAN in networking).
A tariff prices power flowing from specified sources to specified destinations.

When you configure a tariff, HAEO automatically:

1. Assigns tag IDs to source devices
2. Propagates tags across all connections in the network
3. Places tag-scoped pricing at the destination
4. Ensures source devices only produce power on their own tag

The optimizer considers tariff costs when deciding how to route power, choosing cheaper sources when available.

## Configuration

| Field | Description | Required |
|-------|-------------|----------|
| **Name** | Unique name for this tariff | Yes |
| **Sources** | Nodes where the power originates (multi-select, or "any") | Yes |
| **Destinations** | Nodes where the power is consumed (multi-select, or "any") | Yes |
| **Price Source→Target** | Cost per kWh for power flowing in this direction | No |
| **Price Target→Source** | Cost per kWh for power flowing in reverse | No |

### Source and Destination Selection

- **Specific nodes**: Select one or more devices. The tariff applies to power from any selected source to any selected destination.
- **Any**: The tariff applies to power from (or to) any device in the network.

## Examples

### Grid Import Surcharge

Charge $0.05/kWh for any power that comes from the grid:

- **Sources**: Grid
- **Destinations**: Any
- **Price Source→Target**: $0.05/kWh

The optimizer will prefer solar or battery power when available to avoid the surcharge.

### Source-Specific Load Pricing

Different rates for grid vs solar power reaching your load:

**Tariff 1**: Grid → Load: $0.05/kWh
**Tariff 2**: Solar → Load: $0.01/kWh

The optimizer routes solar power to the load first (cheaper), then supplements with grid power as needed.

### Battery Cycling Cost

Model battery wear as a per-kWh cost:

- **Sources**: Battery
- **Destinations**: Any
- **Price Source→Target**: $0.02/kWh

This discourages unnecessary battery cycling unless the savings exceed the wear cost.

## How Tags Work

Tags are assigned automatically — you never configure tag IDs directly.

Each device that produces power (Grid, Solar, Battery when discharging) gets its own tag.
Tags propagate through every connection, so the system always knows where each kWh originated.

When power passes through a battery (charge then discharge), it gets re-tagged:
- Grid → Battery: pays the Grid→Battery tariff (power is grid-tagged)
- Battery → Load: pays the Battery→Load tariff (power is battery-tagged)

This means "laundering" power through a battery doesn't avoid tariffs — it pays at both hops.
If the combined cost is still cheaper than the direct route, the optimizer uses it. This is intentional.

## Model Composition

A tariff does not create new model elements.
Instead, it modifies existing connections by:

1. Adding tag IDs to the connection's tag list
2. Injecting tag-scoped pricing segments at the destination connection

When no tariffs are configured, the system behaves identically to a standard HAEO setup.

## Sensors

| Sensor | Unit | Description |
|--------|------|-------------|
| Per-tag power flows are visible on the connection sensors | kW | Tagged power flow per direction |

## Advanced Usage

### Multiple Tariffs

Multiple tariffs can coexist. Each gets its own tag assignment and scoped pricing.
The optimizer considers all tariffs simultaneously.

### Interaction with Efficiency

Tagged power flows through efficiency segments just like untagged power.
Each tag's flow is reduced by the same efficiency factor.
Tariff pricing applies to the power *after* efficiency losses (at the destination).

## Mathematical Details

See [Tagged Power Flow](../../modeling/tagged-power.md) for the full mathematical formulation.

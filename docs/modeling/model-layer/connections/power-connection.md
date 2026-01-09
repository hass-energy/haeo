# PowerConnection

PowerConnection extends the base [Connection](connection.md) to add power limits, efficiency losses, and transfer pricing.
This is the primary connection type for most user-configured connections.

## Overview

PowerConnection adds these capabilities to the base Connection:

- **Power limits**: Constrain maximum flow in each direction
- **Efficiency**: Model losses during power transfer
- **Pricing**: Add costs/revenues for power flow

## Model Formulation

### Decision Variables

PowerConnection inherits the base Connection variables:

| Variable              | Domain                | Description                      |
| --------------------- | --------------------- | -------------------------------- |
| $P_{s \rightarrow t}$ | $\mathbb{R}_{\geq 0}$ | Power flow from source to target |
| $P_{t \rightarrow s}$ | $\mathbb{R}_{\geq 0}$ | Power flow from target to source |

### Parameters

| Parameter                  | Default   | Description                                  |
| -------------------------- | --------- | -------------------------------------------- |
| `source`                   | Required  | Name of the source element                   |
| `target`                   | Required  | Name of the target element                   |
| `periods`                  | Required  | Time period durations (hours)                |
| `max_power_source_target`  | Unlimited | Maximum power from source to target (kW)     |
| `max_power_target_source`  | Unlimited | Maximum power from target to source (kW)     |
| `efficiency_source_target` | 100%      | Efficiency for source to target flow (0-100) |
| `efficiency_target_source` | 100%      | Efficiency for target to source flow (0-100) |
| `price_source_target`      | None      | Price for source to target flow (\$/kWh)     |
| `price_target_source`      | None      | Price for target to source flow (\$/kWh)     |
| `fixed_power`              | False     | If true, power equals max_power (equality)   |

All parameters except `source`, `target`, and `periods` can be time-varying sequences.

### Constraints

#### Power Limits

When power limits are configured:

$$
0 \leq P_{s \rightarrow t}(t) \leq P_{s \rightarrow t}^{\max}(t) \quad \forall t
$$

$$
0 \leq P_{t \rightarrow s}(t) \leq P_{t \rightarrow s}^{\max}(t) \quad \forall t
$$

If `fixed_power=True`, these become equality constraints (power must equal the limit).

**Shadow prices**: The `connection_shadow_power_max_source_target` and `connection_shadow_power_max_target_source` outputs provide the marginal value of relaxing these constraints.

#### Time-Slice Constraint

When both power limits are set, PowerConnection adds a time-slice constraint preventing simultaneous flow at full capacity in both directions:

$$
\frac{P_{s \rightarrow t}(t)}{P_{s \rightarrow t}^{\max}(t)} + \frac{P_{t \rightarrow s}(t)}{P_{t \rightarrow s}^{\max}(t)} \leq 1 \quad \forall t
$$

This models physical limitations of bidirectional devices (e.g., inverters that can't simultaneously charge and discharge at full rate).

### Power Balance Interface

PowerConnection overrides the base Connection's power balance to apply efficiency losses:

**At source element:**

$$
P_{\text{into\_source}}(t) = P_{t \rightarrow s}(t) \cdot \eta_{t \rightarrow s}(t) - P_{s \rightarrow t}(t)
$$

**At target element:**

$$
P_{\text{into\_target}}(t) = P_{s \rightarrow t}(t) \cdot \eta_{s \rightarrow t}(t) - P_{t \rightarrow s}(t)
$$

**Key concept:**
Power leaving an element is not multiplied by efficiency, but power arriving at an element is multiplied by efficiency (losses occur during transmission).

### Cost Function

If pricing is configured, PowerConnection contributes to the objective function:

$$
\text{Cost} = \sum_{t} \left[ c_{s \rightarrow t}(t) \cdot P_{s \rightarrow t}(t) + c_{t \rightarrow s}(t) \cdot P_{t \rightarrow s}(t) \right] \cdot \Delta t
$$

where $\Delta t$ is the time period in hours.

## Physical Interpretation

**Bidirectional flow:**
Both directions can be active simultaneously in the optimization model, though typically only one direction will have non-zero flow at any given time.
Misconfigurations can result in both being used if the connection can arbitrage power.

**Efficiency modeling:**
Represents real-world losses (inverter efficiency, transmission losses, etc.).
Applied to power arriving at destination.
Can vary over time.

**Pricing:**
Models transmission fees, wheeling charges, or connection costs.
Can vary over time.
Independent pricing for each direction.

## Use Cases

### Unidirectional Connection

Solar → Node (generation only):

```yaml
max_power_source_target: sensor.solar_forecast
max_power_target_source: 0  # or omit
```

### Bidirectional Connection

Grid ↔ Node (import/export):

```yaml
max_power_source_target: 10  # export limit (kW)
max_power_target_source: 10  # import limit (kW)
price_source_target: sensor.export_price
price_target_source: sensor.import_price
```

### Inverter with Losses

DC Node ↔ AC Node:

```yaml
max_power_source_target: 5  # inverting capacity (kW)
max_power_target_source: 5  # rectifying capacity (kW)
efficiency_source_target: 97  # DC→AC efficiency (%)
efficiency_target_source: 96  # AC→DC efficiency (%)
```

### Fixed Power Flow

Load consumption:

```yaml
max_power_target_source: sensor.load_forecast
fixed_power: true  # consumption equals forecast exactly
```

## Configuration Impact

| Configuration                  | Behavior                             |
| ------------------------------ | ------------------------------------ |
| Only `max_power_source_target` | Unidirectional flow only             |
| Both power limits set          | Bidirectional flow allowed           |
| No power limits (unset)        | Unlimited flow in both directions    |
| Power limit = 0                | No flow allowed in that direction    |
| Efficiency < 100%              | Power losses during transmission     |
| Price set                      | Cost added to optimization objective |
| `fixed_power=True`             | Power equals limit (equality)        |

## Next Steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection (base)**

    ---

    Base class for lossless flow.

    [:material-arrow-right: Connection formulation](connection.md)

- :material-file-document:{ .lg .middle } **User configuration**

    ---

    Configure connections in Home Assistant.

    [:material-arrow-right: Connection configuration](../../../user-guide/elements/connections.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/elements/power_connection.py)

</div>

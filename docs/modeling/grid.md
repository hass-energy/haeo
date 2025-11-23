# Grid Modeling

The grid element models bidirectional utility connection with time-varying pricing for import and export.

## Model Formulation

### Decision Variables

For each time step $t$:

- $P_{\text{import}}(t)$: Power imported from grid (kW)
- $P_{\text{export}}(t)$: Power exported to grid (kW)

### Parameters

- $p_{\text{import}}(t)$: Import price (\$/kWh) - from `import_price` sensors
- $p_{\text{export}}(t)$: Export price (\$/kWh) - from `export_price` sensors
- $P_{\text{import}}^{\max}$: Max import (kW) - from `import_limit` config (optional)
- $P_{\text{export}}^{\max}$: Max export (kW) - from `export_limit` config (optional)

### Constraints

#### Non-negativity

$$
P_{\text{import}}(t) \geq 0, \quad P_{\text{export}}(t) \geq 0
$$

#### Power Limits

If configured:

$$
P_{\text{import}}(t) \leq P_{\text{import}}^{\max}, \quad P_{\text{export}}(t) \leq P_{\text{export}}^{\max}
$$

### Cost Contribution

$$
C_{\text{grid}} = \sum_{t=0}^{T-1} \left( P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \right) \cdot \Delta t
$$

Import is positive cost. Export is negative cost (revenue).

## Physical Interpretation

**Import**: Grid supplies power when generation (solar, battery) is insufficient.

**Export**: Grid absorbs excess power from solar or battery discharge.

**Simultaneous import/export**: Optimizer won't do this - it increases cost without benefit.

**Unlimited grid**: If no limits configured, grid can always balance power needs.

## Configuration Impact

| Parameter    | Lower Value                     | Higher Value                            |
| ------------ | ------------------------------- | --------------------------------------- |
| Import limit | Risk infeasibility if too low   | More flexibility, higher potential cost |
| Export limit | Wasted solar/battery if too low | More revenue potential                  |
| Import price | Lower grid costs                | Incentivizes self-consumption           |
| Export price | Less incentive to export        | More revenue from exports               |

**Time-varying prices**: Enable optimization value through time-shifting with battery.

**Flat pricing**: Limited optimization benefit - battery only useful for solar storage.

## Related Documentation

<div class="grid cards" markdown>

- :material-file-document:{ .lg .middle } **User configuration guide**

    ---

    Configure grids in your Home Assistant setup.

    [:material-arrow-right: Grid configuration](../user-guide/elements/grid.md)

- :material-network:{ .lg .middle } **Network modeling**

    ---

    Understand how elements interact in the network model.

    [:material-arrow-right: Network modeling overview](index.md)

- :material-code-braces:{ .lg .middle } **Implementation**

    ---

    View the source code for the grid element model.

    [:material-arrow-right: Source code](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/model/grid.py)

</div>

# Objective Function

The objective function defines what HAEO optimizes: minimizing total cost.

## Formulation

$$
\text{Total Cost} = \sum_{t} \left( C_{\text{import}}(t) - C_{\text{export}}(t) + C_{\text{storage}}(t) \right)
$$

Where:

- $C_{\text{import}}$: Cost of importing from grid
- $C_{\text{export}}$: Revenue from exporting
- $C_{\text{storage}}$: Battery degradation costs

This is minimized subject to all system constraints.

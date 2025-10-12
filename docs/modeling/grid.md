# Grid Modeling

How HAEO models grid import and export.

## Decision Variables

- $P\_{\text{import}}(t)$: Power imported from grid
- $P\_{\text{export}}(t)$: Power exported to grid

## Cost Contribution

$$
C*{\text{grid}}(t) = P*{\text{import}}(t) \cdot p*{\text{import}}(t) - P*{\text{export}}(t) \cdot p\_{\text{export}}(t)
$$

## Constraints

Optional power limits:

$$
0 \leq P*{\text{import}}(t) \leq P*{\text{import}}^{\max}
$$

$$
0 \leq P*{\text{export}}(t) \leq P*{\text{export}}^{\max}
$$

See [grid configuration](../user-guide/entities/grid.md) for details.

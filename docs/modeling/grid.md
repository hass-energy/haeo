# Grid Modeling

How HAEO models grid import and export.

## Decision Variables

- \(P_{\text{import}}(t)\): Power imported from grid
- \(P_{\text{export}}(t)\): Power exported to grid

## Cost Contribution

\[ C_{\text{grid}}(t) = P_{\text{import}}(t) \cdot p_{\text{import}}(t) - P_{\text{export}}(t) \cdot p_{\text{export}}(t) \]

## Constraints

Optional power limits:
\[ 0 \leq P_{\text{import}}(t) \leq P_{\text{import}}^{\max} \]
\[ 0 \leq P_{\text{export}}(t) \leq P_{\text{export}}^{\max} \]

See [grid configuration](../user-guide/entities/grid.md) for details.

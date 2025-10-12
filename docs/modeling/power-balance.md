# Power Balance and Network Structure

How HAEO models the network graph and enforces power balance.

## Graph Structure

HAEO represents your energy system as a directed graph:

- **Nodes**: Entities and net points
- **Edges**: Connections with power flow

## Power Balance Constraint

At each net entity and time step:

$$
\sum*{\text{in}} P*{\text{in}}(t) = \sum*{\text{out}} P*{\text{out}}(t)
$$

This is Kirchhoff's current law applied to power.

## Implementation

For a net entity with inbound connections $\mathcal{C}_{\text{in}}$ and outbound connections $\mathcal{C}_{\text{out}}$, the power balance constraint is:

$$
\sum_{c \in \mathcal{C}_{\text{in}}} P_c(t) = \sum_{c \in \mathcal{C}_{\text{out}}} P_c(t)
$$

This is implemented by iterating over each time step and summing the power variables from all connected entities:

```python
for t in range(n_periods):
    inflow = sum(connection.power[t] for connection in net.inbound)
    outflow = sum(connection.power[t] for connection in net.outbound)
    problem += inflow == outflow
```

Each connection contributes its power variable to either the inflow or outflow sum, and the LP solver ensures these are equal at every time step.

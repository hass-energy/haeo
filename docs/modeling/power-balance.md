# Power Balance and Network Structure

How HAEO models the network graph and enforces power balance.

## Graph Structure

HAEO represents your energy system as a directed graph:
- **Nodes**: Entities and net points
- **Edges**: Connections with power flow

## Power Balance Constraint

At each net entity and time step:

\[ \sum_{\text{in}} P_{\text{in}}(t) = \sum_{\text{out}} P_{\text{out}}(t) \]

This is Kirchhoff's current law applied to power.

## Implementation

=== "Mathematical View"
    
    For a net entity with connections \(\mathcal{C}_{\text{in}}\) and \(\mathcal{C}_{\text{out}}\):
    
    \[ \sum_{c \in \mathcal{C}_{\text{in}}} P_c(t) = \sum_{c \in \mathcal{C}_{\text{out}}} P_c(t) \]

=== "Code View"
    
    ```python
    for t in range(n_periods):
        inflow = sum(connection.power[t] for connection in net.inbound)
        outflow = sum(connection.power[t] for connection in net.outbound)
        problem += inflow == outflow
    ```

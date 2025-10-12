# Connection Modeling

How HAEO models power flow constraints between entities.

## Power Flow Variable

Each connection has a power variable $P_c(t)$.

## Constraints

Optional min/max limits:

$$
P_{\min} \leq P_c(t) \leq P_{\max}
$$

Negative $P_{\min}$ allows bidirectional flow.

## Integration

Connection power flows participate in power balance equations at source and target entities.

See [connections guide](../user-guide/connections.md).

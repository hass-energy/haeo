# Load Modeling

How HAEO models energy consumption.

## Constant Load

Fixed power consumption:

$$
P_{\text{load}}(t) = P_{\text{constant}} \quad \forall t
$$

## Forecast Load

Variable power from forecast data:

$$
P_{\text{load}}(t) = P_{\text{forecast}}(t)
$$

Forecasts are provided by Home Assistant sensors.

See [load configuration](../user-guide/entities/loads.md) for setup.

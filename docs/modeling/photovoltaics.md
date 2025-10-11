# Photovoltaics Modeling

How HAEO models solar generation.

## Generation

Solar power from forecast:
\[ P_{\text{solar}}(t) = P_{\text{forecast}}(t) \]

## Curtailment

If enabled, solar can be reduced:
\[ 0 \leq P_{\text{solar}}(t) \leq P_{\text{forecast}}(t) \]

Optimizer may curtail when:
- Export prices are negative
- Battery is full and load is low
- Grid export is limited

See [photovoltaics configuration](../user-guide/entities/photovoltaics.md).

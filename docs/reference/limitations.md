# Known limitations

This reference summarises the main boundaries of the Home Assistant Energy Optimization (HAEO) integration so you can design scenarios that remain reliable.

## Optimization model

HAEO solves each planning cycle with linear programming (LP).
The method delivers deterministic results and scales predictably with the number of elements and time periods in your network, but actual solve time still depends on hardware capabilities and input data quality.

Because the model is linear:

- Non-linear effects such as temperature dependent efficiency or stepped tariff curves need to be approximated with constants.
- Battery and inverter efficiency values remain fixed for each time step.
- The objective emphasises cost; other goals such as cycle life or demand charge avoidance require automation logic outside HAEO.

## Forecasting and external data

HAEO relies on forecasts sourced from other Home Assistant integrations.
If forecasts are missing or inaccurate, the optimiser can only provide best-effort recommendations.

- Long horizons introduce higher uncertainty, so review recommendations before automating critical actions.
- When forecasts are unavailable you can fall back to constant values, but optimisation results will remain conservative.
- Consult the [horizon guidance](../user-guide/configuration.md#horizon-hours) when you need to balance planning depth against forecast reliability.

## Network modelling

HAEO supports multi-node networks with batteries, loads, generators, and grid connections that share a common bus.
It does not model phase imbalance, reactive power flows, transformer losses, or voltage constraints, so topology should capture energy balances instead of detailed electrical behaviour.

## Battery representation

Battery elements capture state of charge limits, maximum charge and discharge power, and round-trip efficiency.
They do not model thermal behaviour, degradation curves, or manufacturer-specific characteristics.
Configure conservative limits and keep device firmware safeguards active if you need to protect hardware.

## Control scope and cadence

HAEO publishes recommendations to Home Assistant sensors but does not drive hardware directly or provide rapid feedback.
Real-time control remains the responsibility of inverter integrations, battery management systems, and your automations.
Updates combine a polling interval with event-driven refreshes, so expect runs every few minutes plus additional triggers when monitored sensors change.
HAEO is unsuitable for services that demand sub-minute responses or fast grid support.

## Data expectations

Each optimisation cycle needs valid values for the elements in your network.
Provide battery capacity and state of charge, at least one load or generator profile, and pricing information for grid import or export.
Historical data improves forecasting accuracy, so new installations may produce conservative recommendations until enough history is collected.

## Platform expectations

HAEO targets Home Assistant 2024.1 or later on Python 3.13+ with a linear programming solver such as CBC or HiGHS available.
Resource constrained systems can run HAEO, but large networks or long horizons may tax CPU and memory resources.
Monitor system metrics and tune horizons or model complexity if you notice sustained pressure on the host.

## Working within the boundaries

- Keep network models focused on variables you can measure or control.
- Use Home Assistant automations to add safety logic, device-specific limits, and staged responses.
- Review optimisation status sensors regularly; sustained `failed` or `infeasible` states usually mean a required input is missing or conflicting.
- Start with manual review of recommendations before enabling fully automated control loops.

## Monitoring and support

Watch for warning signs such as repeated `failed` or `infeasible` states, rising CPU usage, or sensors that stop updating.
Reduce problem size, verify forecasts, and confirm sensor connectivity before retrying.

If you encounter a limitation that blocks your use case, visit the [HAEO GitHub issues](https://github.com/ha-energy-optimiser/haeo/issues) page or open a [discussion](https://github.com/ha-energy-optimiser/haeo/discussions) with scenario details.
Community feedback guides future improvements, so share the context behind your request whenever possible.

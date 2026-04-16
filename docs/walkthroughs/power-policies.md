# Power policies

This guide demonstrates configuring power policies to control how energy flows between elements and at what cost.
Policies let the optimizer make better decisions by distinguishing the value of power based on where it comes from and where it goes.

## What are power policies?

Without policies, the optimizer treats all power flows equally — a kilowatt from solar feeding the grid is the same as a kilowatt from the battery feeding a load.
Policies add source-to-target pricing that tells the optimizer "power flowing from Solar to Grid costs \$0.02/kWh" while "power flowing from Solar to Load costs \$0.00/kWh."

This lets you model real-world scenarios like:

- **Solar self-consumption**: Free solar power to loads, but export has feed-in tariff costs
- **Battery export control**: Battery discharge to loads is cheap, but grid export is expensive
- **Grid charging constraints**: Grid power to the battery incurs a premium

## Prerequisites

This guide builds on the [Sigenergy System walkthrough](sigenergy-system.md).
The setup block below replays that configuration automatically.

```guide-setup
run_guide("sigenergy-system")
```

## Adding policies

Each policy controls one direction of power flow between elements.
Click **Policies** to add each rule — subsequent rules are appended to the same subentry.

### Step 1: Solar export pricing

Solar power sent to the grid earns only the feed-in tariff rate of \$0.02/kWh, while solar power used locally by loads is free.

```guide
add_policies(
    page,
    name="Solar to Grid",
    source="Solar",
    target="Grid",
    price=0.02,
)
```

!!! info "Why price solar exports?"

    Without a policy, the optimizer has no way to distinguish solar power used locally from solar power exported.
    By pricing the Solar → Grid flow at \$0.02/kWh (the feed-in tariff), the optimizer prefers local consumption over export when both options are available.

### Step 2: Battery export policy

This policy makes battery discharge to the grid expensive, encouraging the optimizer to save battery power for local use.

```guide
add_policies(
    page,
    name="Battery to Grid",
    source="Battery",
    target="Grid",
    price=0.10,
)
```

!!! tip "Battery export pricing"

    Setting a high price (\$0.10/kWh) on Battery → Grid flow means the optimizer will only export battery power when it is profitable enough to justify the cost.
    Battery power is better used to offset grid imports.

### Step 3: Battery to load policy

A low price indicates that using battery power for loads is preferred.

```guide
add_policies(
    page,
    name="Battery to Load",
    source="Battery",
    target="Constant Load",
    price=0.02,
)
```

### Step 4: Grid charging policy

Price grid power flowing to the battery to discourage charging unless prices are low enough.

```guide
add_policies(
    page,
    name="Grid to Battery",
    source="Grid",
    target="Battery",
    price=0.05,
)
```

!!! info "Grid charging costs"

    A \$0.05/kWh surcharge on Grid → Battery means the optimizer only charges from the grid when the round-trip savings exceed this cost.
    This models the real efficiency losses and wear costs of grid charging.

### Step 5: Verify and review

Validate that all four policies were saved correctly, then open the reconfigure view to see them.

```guide
validate_policies(hass, expected_rules=[
    "Solar to Grid",
    "Battery to Grid",
    "Battery to Load",
    "Grid to Battery",
])
```

```guide
reconfigure_policies(page)
```

## How policies affect optimization

With these four policies configured, the optimizer now has detailed cost signals:

| Flow           | Price      | Effect                                              |
| -------------- | ---------- | --------------------------------------------------- |
| Solar → Grid   | \$0.02/kWh | Solar exports earn feed-in tariff                   |
| Solar → Load   | Free       | Local solar consumption is preferred                |
| Battery → Grid | \$0.10/kWh | Battery export is expensive — save for local use    |
| Battery → Load | \$0.02/kWh | Battery-to-load is cheap and preferred              |
| Grid → Battery | \$0.05/kWh | Grid charging has a surcharge for efficiency losses |

The optimizer uses these costs alongside grid import/export prices to find the cheapest overall schedule.
For example, if grid import costs \$0.25/kWh, shipping solar to a load (free) is strongly preferred over importing from the grid.

## Next Steps

<div class="grid cards" markdown>

- :material-chart-line:{ .lg .middle } **Shadow prices**

    ---

    See how policy constraints influence optimization marginal costs.

    [:material-arrow-right: Shadow prices](../modeling/shadow-prices.md)

- :material-cog-transfer:{ .lg .middle } **Policy compilation**

    ---

    Understand how rules compile into tags and destination pricing.

    [:material-arrow-right: Compilation pipeline](../developer-guide/policy-compilation.md)

- :material-tune:{ .lg .middle } **Expand your policy set**

    ---

    Add finer-grained source-to-target pricing as your system evolves.

    [:material-arrow-right: Modeling guide](../modeling/tagged-power.md)

</div>

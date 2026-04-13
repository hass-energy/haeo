# Power Policies

This guide demonstrates configuring power policies to control how energy flows between elements and at what cost.
Policies let the optimizer make better decisions by distinguishing the value of power based on where it comes from and where it goes.

## What are power policies?

Without policies, the optimizer treats all power flows equally — a kilowatt from solar feeding the grid is the same as a kilowatt from the battery feeding a load.
Policies add source-to-target pricing that tells the optimizer "power flowing from Solar to Grid costs $0.02/kWh" while "power flowing from Solar to Load costs $0.00/kWh."

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

### Step 1: Create the Policies subentry

Navigate to the HAEO integration page and click **Policies** to add the first policy rule.

The first policy controls solar export pricing — solar power sent to the grid earns only the feed-in tariff rate of $0.02/kWh, while solar power used locally by loads is free.

```guide
add_policies(
    page,
    name="Solar to Grid",
    source="Solar",
    target="Grid",
    price_source_target=0.02,
)
```

!!! info "Why price solar exports?"

    Without a policy, the optimizer has no way to distinguish solar power used locally from solar power exported.
    By pricing the Solar → Grid flow at $0.02/kWh (the feed-in tariff), the optimizer prefers local consumption over export when both options are available.

### Step 2: Add battery export policy

Open the Policies subentry to add more rules.
This policy makes battery discharge to the grid expensive, encouraging the optimizer to save battery power for local use.

```guide
reconfigure_policies(page)

select_policy_menu_option(page, option="Add new policy")

fill_policy_rule(
    page,
    name="Battery to Grid",
    source="Battery",
    target="Grid",
    price_source_target=0.10,
)
```

!!! tip "Battery export pricing"

    Setting a high price ($0.10/kWh) on Battery → Grid flow means the optimizer will only export battery power when it is profitable enough to justify the cost.
    Battery power is better used to offset grid imports.

### Step 3: Add battery to load policy

While still in the policy menu, add a policy for battery discharge to loads.
This low price indicates that using battery power for loads is preferred.

```guide
select_policy_menu_option(page, option="Add new policy")

fill_policy_rule(
    page,
    name="Battery to Load",
    source="Battery",
    target="Constant Load",
    price_source_target=0.02,
)
```

### Step 4: Add grid charging policy

Add a final policy that prices grid power flowing to the battery.
This discourages charging the battery from the grid unless prices are low enough.

```guide
select_policy_menu_option(page, option="Add new policy")

fill_policy_rule(
    page,
    name="Grid to Battery",
    source="Grid",
    target="Battery",
    price_source_target=0.05,
)
```

!!! info "Grid charging costs"

    A $0.05/kWh surcharge on Grid → Battery means the optimizer only charges from the grid when the round-trip savings exceed this cost.
    This models the real efficiency losses and wear costs of grid charging.

### Step 5: Save and verify

Save the policy configuration and verify the setup.

```guide
select_policy_menu_option(page, option="Save and close")

validate_policies(hass, expected_rules=[
    "Solar to Grid",
    "Battery to Grid",
    "Battery to Load",
    "Grid to Battery",
])
```

## How policies affect optimization

With these four policies configured, the optimizer now has detailed cost signals:

| Flow | Price | Effect |
|------|-------|--------|
| Solar → Grid | $0.02/kWh | Solar exports earn feed-in tariff |
| Solar → Load | Free | Local solar consumption is preferred |
| Battery → Grid | $0.10/kWh | Battery export is expensive — save for local use |
| Battery → Load | $0.02/kWh | Battery-to-load is cheap and preferred |
| Grid → Battery | $0.05/kWh | Grid charging has a surcharge for efficiency losses |

The optimizer uses these costs alongside grid import/export prices to find the cheapest overall schedule.
For example, if grid import costs $0.25/kWh, shipping solar to a load (free) is strongly preferred over importing from the grid.

## Next steps

- Explore [shadow prices](../modeling/shadow-prices.md) to see how policies affect constraint costs
- Read about the [policy compilation pipeline](../developer-guide/policy-compilation.md) for technical details
- Add more granular policies as your system grows

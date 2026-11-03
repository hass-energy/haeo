# Actions

HAEO adds three actions to Home Assistant.
`haeo.optimize` runs a new plan straight away,
`haeo.save_diagnostics` saves a diagnostics file for the current moment or a time in the past,
and `haeo.offer_curve` reports how your grid power would change if the price changed.

You can run any of them from **Developer Tools** → **Actions**,
or call it from an automation or script.

## Run an optimization

`haeo.optimize` runs a new optimization for one HAEO system.
It starts immediately instead of waiting for related updates to settle,
and it runs even when the **Auto optimize** switch on your system's network device is off.

| Field  | Required | Description                         |
| ------ | -------- | ----------------------------------- |
| System | Yes      | The HAEO system to run the plan for |

Use it when:

- **Auto optimize** is off and you want to choose when HAEO plans, such as after an automation changes several inputs at once
- You changed something and want to see the new plan without waiting
- You want to check that HAEO can produce a plan from the data it has now

```yaml
action: haeo.optimize
data:
  config_entry: <your HAEO system>
```

In the automation editor, pick the system from the **System** list rather than typing its ID.

The action returns once the optimization finishes.
Its result shows up the same way as any other plan:
the output sensors update when it succeeds,
and the optimization status sensor and a repair issue explain a failure.
See [Understanding results](optimization.md) and [Troubleshooting](troubleshooting.md).

When the planning horizon has just moved on, HAEO may still be loading forecasts for the new periods.
The action then fails with a message saying the forecast inputs are still loading.
HAEO plans by itself once those forecasts have loaded, so you only need to run it again if you turned **Auto optimize** off.

## Save diagnostics

`haeo.save_diagnostics` writes a diagnostics file for one HAEO system.
The file holds your HAEO configuration, the input values the optimizer used, and the resulting plan,
in the same format as **Download diagnostics** on the integration page.

| Field  | Required | Description                                                                         |
| ------ | -------- | ----------------------------------------------------------------------------------- |
| System | Yes      | The HAEO system to save diagnostics for                                             |
| Time   | No       | A past date and time to rebuild the inputs from. Leave it out for the current state |

Use it when:

- You want to report a plan that looked wrong some time ago.
    Set **Time** to that moment and HAEO rebuilds what the optimizer saw from Home Assistant's history.
- You want a file of the current state to attach when you ask for help

The file is saved in the `haeo/diagnostics/` folder of your Home Assistant configuration directory.
Its name includes the time it describes.

A **Time** without a time zone is read in Home Assistant's own time zone.
**Time** needs Home Assistant's recorder, because the recorder is where past values come from.
Without the recorder, the action fails when you set a time.
The [historic diagnostics walkthrough](../walkthroughs/historic-diagnostics.md) shows the steps in the Home Assistant interface.

```yaml
action: haeo.save_diagnostics
data:
  config_entry: <your HAEO system>
  time: '2025-01-01 18:30:00'
```

!!! warning "Privacy"

    The diagnostics file contains your energy configuration and the values of the sensors HAEO reads.
    Review it before you share it publicly.

## Get offer curves

`haeo.offer_curve` answers "if the price for this half hour were different, how much would my home import or export?"
For each interval of the current plan, it lists the average grid power your home would use at every price that interval could have,
with the prices outside it left as forecast.
This is an offer: the information a retailer, aggregator or market operator needs to know how your home responds to a price,
while every decision stays with HAEO in your home.

| Field                | Required | Description                                                                     |
| -------------------- | -------- | ------------------------------------------------------------------------------- |
| System               | Yes      | The HAEO system to get offer curves for                                         |
| Start                | No       | Includes intervals that end after this time. Leave it out to start from now     |
| End                  | No       | Includes intervals that start before this time. Leave it out for the whole plan |
| Interval             | No       | How long a price change lasts, in minutes. Defaults to 30                       |
| Lowest import price  | No       | Lowest average import price per kWh each curve covers. Defaults to -1           |
| Highest import price | No       | Highest average import price per kWh each curve covers. Defaults to 20          |

The plan is split into intervals of this length on the clock, such as each half hour,
and the price changes across the whole of an interval.
How long a price change lasts matters a great deal.
A price that holds for one minute can be met by emptying the battery for that minute at almost no cost to the rest of the plan,
while one that holds for half an hour uses far more of the battery's charge, so the home responds less to it.
The default of 30 minutes is the length of a trading interval in the Australian market and of most price forecasts.
Use 5 minutes for the market's dispatch intervals.
The first interval runs from now to the next boundary, and an interval is never shorter than the plan's own periods in it,
which grow longer further ahead.

The default prices cover the full range of Australian wholesale market prices, -\$1000 to about \$20,000 per MWh.
Each curve always includes the forecast price.

Use it when:

- You want to share how your home would respond to a price, such as with a demand response program or a price-responsive resource trial
- You want to see how much flexibility your home has at a time, and what price it takes to use it

```yaml
action: haeo.offer_curve
data:
  config_entry: <your HAEO system>
  end: '2026-11-03 21:00:00'
response_variable: offers
```

The action returns its result rather than changing any entity, so call it from a script or automation with `response_variable`,
or run it from **Developer Tools** → **Actions** to see the result there.
It looks like this, with one list of intervals for each grid, shortened here:

```yaml
grids:
  Grid:
    - start: '2026-11-03T17:08:00+10:00'
      end: '2026-11-03T17:30:00+10:00'
      import_price: 0.2111
      export_price: 0.1472
      power: -0.7
      offer:
        - {import_price: -1.0, export_price: -1.0639, power: 9.41}
        - {import_price: 0.0021, export_price: -0.0618, power: 1.48}
        - {import_price: 0.1519, export_price: 0.088, power: 0.0}
        - {import_price: 0.2087, export_price: 0.1448, power: -0.7}
        - {import_price: 0.2178, export_price: 0.1539, power: -7.14}
        - {import_price: 0.2424, export_price: 0.1785, power: -8.88}
        - {import_price: 0.2493, export_price: 0.1854, power: -26.34}
```

`import_price`, `export_price` and `power` at the top of an interval are its average forecast prices and planned grid power.
Power is in kW, positive for import and negative for export, like the grid's active power sensor.
Each entry in `offer` is a step: from those prices up to the next step's, the average grid power over the interval would be `power`.
Import and export prices move together, as a change in the wholesale price changes both.

In this example the plan exports 0.7 kW on average at the forecast prices.
If the export price for the interval rose to 15.39c the home would export 7.14 kW, and from 18.54c all it can, 26.34 kW.
Below an export price of 14.48c it would stop exporting,
below an import price of 15.19c it would start importing,
and below an import price of zero it would charge from the grid as fast as it can.

Each curve holds the prices outside its interval at their forecast,
so curves of different intervals do not add up:
a battery's charge can only be spent once,
and a high price across several intervals draws less from it in each than their separate curves show.
For a price change that lasts longer, such as a two-hour event, set **Interval** to its length.
[Offer curves](../modeling/offer-curves.md) explains how they are worked out.

Working out a curve means solving the plan again several times,
so the action can take several seconds for a long plan, or longer on slower hardware.
Set **End** to get curves only for the time you need.
The plan and the output sensors are not changed, and HAEO does not plan again while the action runs.

## Errors

The actions stop with an error message when they cannot run:

| Message                                                              | What it means                                                                                          | What to do                                                          |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------- |
| Config entry … not found                                             | The chosen system no longer exists                                                                     | Pick the system again; it may have been removed and added again     |
| Config entry … is not a HAEO hub                                     | The chosen entry belongs to another integration                                                        | Pick a HAEO system                                                  |
| Config entry … is not loaded                                         | The HAEO system is still starting, failed to start, or is disabled                                     | Check the system on the integration page and fix any reported issue |
| The forecast inputs are still loading …                              | Only from `haeo.optimize`: the horizon has just moved on and forecasts for the new periods are loading | Try again in a moment                                               |
| Saving diagnostics for a past time needs Home Assistant's recorder … | Only from `haeo.save_diagnostics`: you set **Time** but the recorder is not running                    | Leave **Time** out, or enable the recorder                          |
| No history available at time …                                       | Only from `haeo.save_diagnostics`: the recorder has no values at that time for the inputs it names     | Choose a later time, within how long your recorder keeps history    |
| The latest optimization found no plan …                              | Only from `haeo.offer_curve`: the last optimization failed, or none has run yet                        | Fix the reported problem, then try again once a plan is found       |
| The latest plan relaxed constraints …                                | Only from `haeo.offer_curve`: the plan was found with **Relax impossible plans**                       | Fix the conflict the repair issue names                             |
| The lowest import price must be below the highest                    | Only from `haeo.offer_curve`: the price range is empty                                                 | Set **Lowest import price** below **Highest import price**          |

## Next steps

<div class="grid cards" markdown>

- :material-robot-outline:{ .lg .middle } __Automate with HAEO__

    ---

    Use HAEO's plan to control your devices.

    [:material-arrow-right: Automation examples](automations.md)

- :material-refresh:{ .lg .middle } __Understand when HAEO plans__

    ---

    See what starts a new optimization by itself.

    [:material-arrow-right: Data updates](data-updates.md)

- :material-help-circle-outline:{ .lg .middle } __Fix problems__

    ---

    Work through common issues, and attach a diagnostics file when you ask for help.

    [:material-arrow-right: Troubleshooting](troubleshooting.md)

</div>

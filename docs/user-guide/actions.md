# Actions

HAEO adds three actions to Home Assistant.
`haeo.optimize` runs a new plan straight away,
`haeo.save_diagnostics` saves a diagnostics file for the current moment or a time in the past,
and `haeo.offer_curve` reports how your grid power would change if the price changed.

You can run any of them from **Developer Tools** → **Actions**,
or call it from an automation or script.

## Run an optimization

`haeo.optimize` runs a new optimization for one HAEO system and waits for it to finish.
By default it starts immediately instead of waiting for related updates to settle,
and it runs even when the **Auto optimize** switch on your system's network device is off.

| Field       | Required | Description                                                                            |
| ----------- | -------- | -------------------------------------------------------------------------------------- |
| System      | Yes      | The HAEO system to run the plan for                                                    |
| Immediately | No       | On by default. Turn it off to wait out the **Debounce window (seconds)** setting first |

Leave **Immediately** on when you need a new plan now.
Turn it off when an automation calls the action every time something changes,
so changes made close together share one optimization, as automatic optimizations do.

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

The action returns once the next optimization to start has finished,
so a step after it in a script sees the new plan.
If HAEO already had an optimization lined up, the action waits for that one rather than adding another.
When the planning horizon has just moved on and HAEO is still loading forecasts for the new periods,
the optimization waits for them to load.

Its result shows up the same way as any other plan:
the output sensors update when it succeeds,
and the optimization status sensor and a repair issue explain a failure.
When the optimization fails, the action fails too, with the same message the optimization status sensor shows.
See [Understanding results](optimization.md) and [Troubleshooting](troubleshooting.md).

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
Only Home Assistant administrators can run it, because the file is written into the configuration directory.

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

`haeo.offer_curve` answers "what would my home bid for the next settlement interval?"
It lists the average grid power your home would use over that interval at every price it could have,
with the prices of every other interval left as forecast.
This is the offer a generator or a battery makes to a market, one curve for each interval:
a retailer, aggregator or market operator learns how your home responds to a price,
while every decision stays with HAEO in your home.

| Field                | Required | Description                                                                                                    |
| -------------------- | -------- | -------------------------------------------------------------------------------------------------------------- |
| System               | Yes      | The HAEO system to get offer curves for                                                                        |
| Start                | No       | The first curve is for the first whole interval to start at or after this time. Leave it out to start from now |
| End                  | No       | Also returns each later interval that starts before this time. Leave it out for the first interval only        |
| Interval             | No       | Length of your market's settlement interval, in minutes. Defaults to 5                                         |
| Lowest import price  | No       | Lowest average import price per kWh each curve covers. Defaults to -1                                          |
| Highest import price | No       | Highest average import price per kWh each curve covers. Defaults to 20                                         |
| Emissions intensity  | No       | A sensor giving the grid's emissions intensity, to report how each step changes your grid emissions            |

With only a system chosen, the action returns one curve, for the next interval to start.
The interval already under way is left out, since its price is already set.
Your home can keep to that curve whatever the forecast turns out to be:
what it can import or export over the next few minutes depends on the battery's charge and power limits now.
The forecast decides only the prices at which the home responds, through what its stored energy would be worth later.

Set **End** to get the later intervals as well, as a market takes bids for the rest of the day.
Treat those as a guide.
Each one assumes every interval before it goes as forecast, so they do not add up:
a battery's charge can only be spent once, and energy sold in one interval is not there for the next.
Call the action again as each interval comes up, the way a generator rebids.

Set **Interval** to the length of your market's settlement interval.
The default of 5 minutes is that of Australia's National Electricity Market.
The length matters a great deal.
A price that holds for one minute can be met by emptying the battery for that minute at almost no cost to the rest of the plan,
while one that holds for half an hour uses far more of the battery's charge, so the home responds less to it.
For a price change that lasts longer, such as a two-hour demand response event, set **Interval** to its length.

Short intervals give an all-or-nothing curve: a cent or two above the forecast and the battery exports flat out.
Longer intervals give a gentler curve with more steps, as the battery's stored energy is spread across the whole interval.
An interval is never shorter than the plan's own periods in it.
Those grow longer further ahead, often to an hour, so 5 minute curves are only 5 minutes long for the next hour or so.

The default prices cover the full range of Australian wholesale market prices, -\$1000 to about \$20,000 per MWh.
Each curve always includes the forecast price.

Use it when:

- You want to share how your home would respond to a price, such as with a demand response program or a price-responsive resource trial
- You want to see how much flexibility your home has right now, and what price it takes to use it

```yaml
action: haeo.offer_curve
data:
  config_entry: <your HAEO system>
response_variable: offers
```

The action returns its result without changing any entity, so call it from a script or automation with `response_variable`,
or run it from **Developer Tools** → **Actions** to see the result there.
Called at 5:08 pm, it looks like this, with one list of intervals for each grid:

```yaml
grids:
  Grid:
    - start: '2026-11-03T17:10:00+10:00'
      end: '2026-11-03T17:15:00+10:00'
      import_price: 0.2105
      export_price: 0.1467
      power: 0.0
      offer:
        - {import_price: -1.0, export_price: -1.0638, power: 17.548}
        - {import_price: 0.0, export_price: -0.0638, power: 9.253}
        - {import_price: 0.1483, export_price: 0.0845, power: 3.272}
        - {import_price: 0.1498, export_price: 0.086, power: 0.0}
        - {import_price: 0.2136, export_price: 0.1498, power: -2.65}
        - {import_price: 0.2158, export_price: 0.152, power: -7.547}
        - {import_price: 0.2473, export_price: 0.1835, power: -26.747}
```

`import_price`, `export_price` and `power` at the top of an interval are its average forecast prices and planned grid power.
Power is in kW, positive for import and negative for export, like the grid's active power sensor.
Each entry in `offer` is a step: from those prices up to the next step's, the average grid power over the interval would be `power`.
Import and export prices move together, as a change in the wholesale price changes both.

In this example the plan takes nothing from the grid at the forecast prices.
If the export price for the interval rose to 14.98c the home would export 2.65 kW, from 15.2c 7.55 kW, and from 18.35c all it can, 26.75 kW.
Below an import price of 14.98c it would import 3.27 kW, below 14.83c 9.25 kW,
and below an import price of zero it would charge from the grid as fast as it can.

With **Emissions intensity** set, each interval also gives its average `emissions_intensity` in kg/kWh,
and each step gives `emissions`: how many kg the plan's grid emissions over the whole horizon would change by, compared with the plan at the forecast prices.
It counts the battery refilling at other times, so exporting into a high price can raise emissions overall
when the energy is made up later from a dirtier grid.
Exported energy counts as avoiding emissions at the grid's intensity when it is exported.
The sensor can give a single reading or a forecast, in g, kg or t of CO2 or CO2-e per kWh or MWh,
such as an emissions intensity sensor from your region's market data.

[Offer curves](../modeling/offer-curves.md) explains how the curves are worked out and why they make a sound bid.

Working out a curve means solving the plan again several times.
The next interval takes a fraction of a second, and every interval of a long plan can take several seconds, or longer on slower hardware.
The plan and the output sensors are not changed, and HAEO does not plan again while the action runs.

## Errors

The actions stop with an error message when they cannot run:

| Message                                                              | What it means                                                                                       | What to do                                                          |
| -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Config entry … not found                                             | The chosen system no longer exists                                                                  | Pick the system again; it may have been removed and added again     |
| Config entry … is not a HAEO hub                                     | The chosen entry belongs to another integration                                                     | Pick a HAEO system                                                  |
| Config entry … is not loaded                                         | The HAEO system is still starting, failed to start, or is disabled                                  | Check the system on the integration page and fix any reported issue |
| Any optimization error                                               | Only from `haeo.optimize`: the optimization it waited for failed                                    | See [Troubleshooting](troubleshooting.md) for that message          |
| Saving diagnostics for a past time needs Home Assistant's recorder … | Only from `haeo.save_diagnostics`: you set **Time** but the recorder is not running                 | Leave **Time** out, or enable the recorder                          |
| No history available at time …                                       | Only from `haeo.save_diagnostics`: the recorder has no values at that time for the inputs it names  | Choose a later time, within how long your recorder keeps history    |
| The latest optimization found no plan …                              | Only from `haeo.offer_curve`: the last optimization failed, or none has run yet                     | Fix the reported problem, then try again once a plan is found       |
| The plan covers no whole interval …                                  | Only from `haeo.offer_curve`: no interval of that length lies wholly inside the plan from **Start** | Set **Start** inside the plan, or use a shorter **Interval**        |
| The latest plan relaxed constraints …                                | Only from `haeo.offer_curve`: the plan was found with **Relax impossible plans**                    | Fix the conflict the repair issue names                             |
| The lowest import price must be below the highest                    | Only from `haeo.offer_curve`: the price range is empty                                              | Set **Lowest import price** below **Highest import price**          |
| The emissions intensity sensor … has no reading                      | Only from `haeo.offer_curve`: the sensor is missing or unavailable                                  | Check the sensor, or leave **Emissions intensity** out              |
| The emissions intensity sensor … is in …                             | Only from `haeo.offer_curve`: the sensor's unit is not a mass of CO2 per unit of energy             | Choose a sensor in g, kg or t per kWh or MWh                        |

## Next steps

<div class="grid cards" markdown>

- :material-robot-outline:{ .lg .middle } __Automate with HAEO__

    ---

    Use HAEO's plan to control your devices.

    [:material-arrow-right: Automating your hardware](automations.md)

- :material-refresh:{ .lg .middle } __Understand when HAEO plans__

    ---

    See what starts a new optimization by itself.

    [:material-arrow-right: Data updates](data-updates.md)

- :material-help-circle-outline:{ .lg .middle } __Fix problems__

    ---

    Work through common issues, and attach a diagnostics file when you ask for help.

    [:material-arrow-right: Troubleshooting](troubleshooting.md)

</div>

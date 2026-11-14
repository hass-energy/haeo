# Offer curves

An offer curve says how much power a home would take from the grid over a window of time at each price that window could have,
with every price outside the window left as forecast.
It answers "what does this home bid for the next settlement interval?",
the question a generator answers with a quantity in each of a set of price bands.
The `haeo.offer_curve` [action](../user-guide/actions.md#get-offer-curves) returns a grid's curve over each interval of time it is given.

## What the curve is

Shifting the grid prices of every period in a window $W$ by $d$ adds $d$ times the window's net grid energy to the cost of every plan.
The cheapest cost as a function of the shift,

$$
V(d) = \min_x \left( c^\top x + d \sum_{t \in W} E_t(x) \right),
$$

is a minimum of lines in $d$, one per plan, so it is concave and piecewise linear.
Its slope at any shift is the window's net grid energy in the cheapest plan there,
and the curve reports it as the average power over the window.
That power is therefore a step function of the price that never rises as the price rises:
each step is a range of prices over which one plan stays cheapest,
and each edge between steps is a price at which the next kilowatt-hour is worth more somewhere else,
such as in the battery for later, in an EV, or exported outside the window.

The shift moves the import and export prices together,
as a change in the wholesale price passes through to both.
The curve covers every response the model can make, across the whole horizon:
a higher price in one window can empty the battery into it and refill it in a later one.

### Why a window

The window is the market's settlement interval, the time one price holds for, and the response depends heavily on its length.
A shift in one short period can be met by moving a little energy into or out of it,
which costs the rest of the plan almost nothing,
so a curve of a single minute shows nearly the full power of the battery for a small change in price.
Over a longer window the same response uses far more energy and costs the rest of the plan far more.
On scenario 7, raising both prices by 3.5c/kWh from the start of the plan gives:

| Window     | Average export |
| ---------- | -------------- |
| 1 minute   | 26.8 kW        |
| 5 minutes  | 15.3 kW        |
| 30 minutes | 11.0 kW        |

The action traces a curve over each interval it is given, which the caller sets to the intervals its market settles on.
A curve traced over any other length promises the wrong power.
The shift is the same throughout the window, so the price shape within it is kept,
as a change in the wholesale price leaves the tariffs added to it as they are.
A shift is used rather than a scaling of the price, since scaling does nothing to a price of zero
and turns a negative price more negative as it raises a positive one.

Because the net energy is the slope of $V$, it is the same in every cheapest plan at a shift that is not on an edge.
The curve therefore needs none of the tie-breaking the plan itself uses,
and it is traced against the cost alone.

### How window length shapes the curve

Across the scenario networks, at the start of the plan, at the evening peak and at midday:

- Short windows give an almost vertical curve.
    The battery's power limit binds before its stored energy does, so a cent or two above the forecast moves it from idle to flat out.
- Long windows give a gentler curve with more steps.
    Stored energy binds first, and the average power it supports falls as the window grows.
- The energy moved into a window rises with its length and then levels off once the window outlasts the battery,
    at about 27 kWh near the start of scenario 7.
- The curve's shape can change with length in either direction,
    since a longer window also takes in periods whose forecast prices sit nearer or further from a step.
- A window shorter than the period it falls in gives a blurred curve.
    Periods grow to an hour further ahead, and the plan cannot do one thing in part of a period and another in the rest.

### Windows and periods

A window can start and end anywhere in the plan, whatever the plan's periods are.
The model holds the power constant through a period, so the energy a window takes from a period is that power times the time the window spends in it.
The shift is priced on that share of the period's energy, and the window's forecast prices are weighted the same way.
Windows can overlap, since each curve is traced on its own.

Each window takes well under a second to trace.

## Emissions

Given the grid's emissions intensity in each period, each step also reports the change in the plan's grid emissions over the whole horizon,
compared with the plan at the forecast prices.
The power in a window is the same in every cheapest plan at a price off a step's edge,
but how the rest of the plan makes up for it need not be.
The emissions are therefore also minimized among equally cheap plans,
with a weight too small to move a step's edge by more than a thousandth of a cent per kWh.

Because the whole horizon is counted, the emissions of a step include the battery refilling elsewhere.
Exporting into a high price can raise emissions overall, when the energy is made up later from a dirtier grid,
so a price signal and a carbon signal can ask for opposite responses.

## How it is traced

The edges are found with Eisner and Severance's method for parametric linear programs.
Solve at the bottom and top of a price range, and find where the two plans' cost lines cross.
Solve again at that crossing.
If its cost is what the lines say, the crossing is the only edge between them;
otherwise the cheaper plan found there splits the range, and each half is searched the same way.
A curve with $k$ steps takes $2k + 1$ solves.

Each solve changes only costs, so the model keeps its shape and HiGHS warm-starts from the last basis.
The solves run on a copy of the solved model,
so the plan, its shadow prices, and the basis the next optimization starts from are left as they are.
A plan found by [relaxing constraints](../user-guide/troubleshooting.md#relax-impossible-plans) has no curve,
since its model has its bounds back once the plan is read.

[`core/model/offer.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/model/offer.py) traces the curve of any flow,
and [`core/adapters/offer.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/adapters/offer.py) applies it to a grid's net import.

### Why not ranging

HiGHS's cost ranging gives the range of one column's cost over which the basis stays optimal.
Stepping past the end of each range and solving again also traces the curve,
and a ranging step for both grid prices at once can be read from the reduced costs at the basis.
It was measured against Eisner and Severance on the scenario networks, tracing every period from -1 to 20 \$/kWh:

| Scenario | Periods | Columns | Eisner and Severance | Ranging steps                              |
| -------- | ------- | ------- | -------------------- | ------------------------------------------ |
| 1        | 96      | 2,114   | 0.97 s               | 2.7 s                                      |
| 6        | 192     | 6,914   | 8.7 s                | 202 s, 9 periods stopped after 2,000 steps |

Both found the same curves where ranging finished.
A basis change is not a change in the energy:
the LPs are degenerate, so most basis changes move nothing the curve shows,
and runs of them a fraction of a cent apart leave ranging creeping forward.
Eisner and Severance solves only where the cost says another step must be.

## The curve as a bid

Each window's curve is a set of price bands with a quantity in each,
the shape a scheduled resource's bid takes in a market.
Import steps read as a load bid: the power the home would consume at or below each price.
Export steps read as a generation offer: the power it would supply at or above each price.

A home too small to move the market price does best by bidding the curve as it is.
At whatever price the interval clears, the quantity the curve gives is the one the cheapest plan takes at that price,
so no other bid leaves the home better off at any price.
The edges are the home's marginal costs: what the next kilowatt-hour is worth elsewhere in the plan.

### The next interval

The next interval's curve is a bid the home can deliver.
What it can import or export over the next few minutes is set by its state of charge and power limits now.
The forecast sets only where the edges sit, through what stored energy is worth later.
A wrong forecast therefore misprices the bid, which costs the home, and the power it offered can still be delivered.

### Later intervals

A later interval's curve depends on what happens before it, through the energy left in storage.
Each curve holds every price outside its window at forecast,
so curves of different windows do not add up, since the battery's energy can only be spent once:
a price spike across several windows draws less from it in each than the separate curves suggest.
The home's response to every price at once is the slope of $V$ in all the shifts together, which no set of separate curves can hold.

Markets meet the same problem by rebidding.
A generator bids each later interval for the state it expects to reach it in, and bids again as that state changes.
The later curves are bids of that kind:
each assumes every interval before it clears at its forecast price,
and calling the action again after the next optimization replaces them.

A price change that lasts longer than one interval, such as a demand response event,
is better described by a curve over a window of its length.

## Next steps

<div class="grid cards" markdown>

- :material-play-circle-outline:{ .lg .middle } __Get offer curves__

    ---

    Call the action and read its response.

    [:material-arrow-right: Actions](../user-guide/actions.md#get-offer-curves)

- :material-currency-usd:{ .lg .middle } __Shadow prices__

    ---

    The value of one more unit of a limit at the plan.

    [:material-arrow-right: Shadow prices](shadow-prices.md)

</div>

# Input entities

Input entities are an intermediate layer between external Home Assistant sensors and the optimization model.
They expose each configured input as a Number or Switch entity that users can inspect, and edit when it holds a constant.

## Purpose

HAEO's input layer provides:

- **Visibility**: Users see loaded values as standard Home Assistant entities
- **Editability**: Constant values can be changed for what-if analysis or through automations
- **Decoupling**: Data loading happens independently of optimization cycles
- **Alignment**: All inputs share synchronized forecast horizons

## Architecture

```mermaid
graph LR
    subgraph "External"
        Sensors[HA sensors]
    end

    subgraph "Input layer"
        Stores[runtime_data.input_stores]
        IE[Input entities]
        HM[HorizonManager]
    end

    subgraph "Optimization"
        Coord[Coordinator]
    end

    Sensors -->|load| Stores
    HM -->|horizon| Stores
    Stores --> IE
    Stores -->|values and listeners| Coord
```

An `InputStore` ([`core/data/input_store.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/core/data/input_store.py)) is the single source of truth for one field's value.
`build_input_stores` in [`input_stores.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/input_stores.py) creates the stores during setup, before any entity exists, and keeps them in `runtime_data.input_stores` keyed by `(element_name, field_path)`.
Each store is bound to a `SubentryStorage`, so an edited constant is written back to the element's subentry.

Two loaders in [`inputs/`](https://github.com/hass-energy/haeo/tree/main/custom_components/haeo/inputs) keep the stores loaded, and the Number and Switch entities only display them, following each store through `add_listener`.
A store therefore loads whether or not its entity is enabled.
The coordinator reads each store's resolved `value` and subscribes to changes with `add_listener`, rather than reading sensors itself.

## Input fields

Which config fields become inputs is derived from each element type's schema.
`get_input_fields()` in [`elements/__init__.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/elements/__init__.py) builds the `InputFieldInfo` for each field from its field hints, describing the entity description, output type, direction, and time-series behavior.
`get_list_input_fields()` does the same for list fields, such as policy rules.

## Entity creation

Each field takes one of three values in the config flow, through the ChooseSelector pattern documented in [Config flow development](config-flow.md#chooseselector-config-flow-pattern):

- **Constant**: The store holds the value in **editable** mode, and the entity can change it.
- **Entity**: The store loads the selected sensors in **driven** mode, and the entity shows the loaded value read-only.
- **None**: No store or entity is created, and the field is omitted from the model.

Fields whose values are on or off, status and availability fields, become Switch entities, and every other field a Number entity.
A switch over a time series is on when its current period is, and its `forecast` attribute holds each period's value.

An element type with surfaced policy prices also gets mirror entities on its own device that wrap the policy rule's store, so editing either updates the one stored value.

## Loading

Driven stores resolve their sources with `resolve_field`, which extracts, combines, and fuses forecast data.
See the [Data loading guide](data-loading.md) for the pipeline.

Stores load at setup, when their source sensors change, and when the [HorizonManager](horizon-manager.md) advances.
A source update that resolves to the same value, timestamps, and availability as before does not notify the coordinator.

### Holding a reading through a gap

A store keeps the last state with a reading from each of its sources.
When a source has no reading, the store resolves from that last reading instead, alongside the live readings of its other sources and over the current horizon, so the input stays available and the coordinator keeps optimizing.
Only a source's own state is held.
A state the calendar input loader annotates with data fetched for the current horizon, a calendar's events or a meter's totals, describes only that horizon, so a calendar whose events no longer cover the horizon, or a meter without a reading, makes its input unavailable at once.

The hold lasts for the hub's `input_hold_seconds` from that moment, 60 seconds unless set otherwise, and 0 turns it off.
It is timed on the monotonic clock, so setting the wall clock does not lengthen or end it.
Once it passes, the store is unavailable exactly as it is without a hold, and the coordinator's `unavailable_input` repair issue names every source with no reading, including any still within its hold.
A source that has never had a reading is never held, so setup still waits for every input.
A source that reads again is live at once, and a later gap starts a new hold.

A hold starting or ending leaves the value as it is, so it does not notify the store's `add_listener` listeners, and the coordinator does not re-optimize for it.
It notifies `add_hold_listener` listeners instead: the input entities, which update the attributes naming the held source, and `InputHoldExpiry`.
A source that stays without a reading does not change, so nothing would reload its store when the hold passes.
`InputHoldExpiry` in [`inputs/hold_expiry.py`](https://github.com/hass-energy/haeo/blob/main/custom_components/haeo/inputs/hold_expiry.py) waits for the earliest `hold_expires_at`, and then calls `expire_holds()` on each store and notifies those that became unavailable.

Diagnostics capture a held source as its last reading with a `haeo_held_since` attribute, the time it lost that reading, so a replay resolves the same value and the held reading is told apart from a live one.

The Home Assistant side of reading inputs lives in [`inputs/`](https://github.com/hass-energy/haeo/tree/main/custom_components/haeo/inputs):

- `ha_state_machine.py` adapts Home Assistant's state machine to the `StateMachine` protocol the core loaders read through.
- `source_loader.py` loads every other store, from its source sensors or its constant.
    Sensors that change together in one pass share one reload.
- `hold_expiry.py` makes a store unavailable once a reading it holds through a gap is too old.
- `calendar_loader.py` loads stores that read calendars, since a calendar's state carries only its current event.
    It fetches events from the horizon's start to a day past its end in the background, and hands them to the core loader as a state attribute, so horizon rolls resolve from events already fetched.
- `meter_history.py` keeps the running totals of meter fields through resets, from recorder statistics and later state changes.
    When the statistics cannot be read, the calendar loader retries in the background after its next load, without holding loads up.

`core/annotated_state.py` merges those calendar events and meter totals into entity states in the same form diagnostics capture, so live runs and replays read inputs the same way.

## Entity attributes

All input entities expose extra state attributes for debugging and automation:

| Attribute      | Description                                                |
| -------------- | ---------------------------------------------------------- |
| `config_mode`  | `editable` or `driven`                                     |
| `element_name` | Element name                                               |
| `element_type` | Element type                                               |
| `field_name`   | Configuration field name                                   |
| `field_path`   | Path to the field within the element's config              |
| `field_type`   | Output type of the field, such as power or price           |
| `time_series`  | Whether values vary per period                             |
| `direction`    | Power flow direction, when the field has one               |
| `forecast`     | `{time, value}` points across the horizon, for time series |

Driven Number entities also expose `source_entities`, listing the entity IDs that provide the data, and driven Switch entities expose `source_entity`, the one entity they follow.

While a driven input holds a reading through a gap, it also exposes `held_source_entity`, the held source that lost its reading first, and `held_since`, when that source lost it.
Both are absent while every source has a reading, so automations can tell a held value from a live one.

## Entity naming and category

Input entities use translated names, and belong to the device of the element they configure.
Their unique IDs come from `element_unique_id` in `unique_id.py`.

Input entities use `EntityCategory.CONFIG`, so they show on device pages rather than default dashboards.

## Related documentation

<div class="grid cards" markdown>

- :material-timer-outline:{ .lg .middle } **Horizon manager**

    ---

    Synchronized forecast time windows.

    [:material-arrow-right: Horizon manager guide](horizon-manager.md)

- :material-database:{ .lg .middle } **Data loading**

    ---

    How the field resolver extracts and aligns data.

    [:material-arrow-right: Data loading guide](data-loading.md)

- :material-sync:{ .lg .middle } **Coordinator**

    ---

    How the coordinator uses pre-loaded input data.

    [:material-arrow-right: Coordinator guide](coordinator.md)

</div>

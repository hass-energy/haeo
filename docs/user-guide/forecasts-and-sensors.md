# Forecasts and Sensors

This guide explains how HAEO uses Home Assistant sensor data to optimize your energy network.

## Overview

HAEO loads data from Home Assistant sensors to understand:

- **Electricity prices** for import and export
- **Solar generation** forecasts
- **Load consumption** patterns

Each sensor provides either a current value or a forecast series, never both.
HAEO automatically detects what data each sensor exposes and combines everything into a unified time series aligned with your optimization horizon.

## How HAEO Uses Sensor Data

When you configure an element like a grid or solar system, you provide one or more sensor entity IDs.
HAEO reads these sensors and extracts either:

- **Present value**: The current sensor reading at the moment optimization starts (for simple sensors)
- **Forecast series**: A list of future timestamped predictions (for forecast-capable sensors)

These values are then processed to create a complete time series covering your optimization horizon.

## Single Sensor Values

The simplest case is a sensor that only provides a current value without any forecast data.

**Example**: A sensor showing current grid import price:

```yaml
entity_id: sensor.current_electricity_price
state: 0.25
```

HAEO reads the value (0.25 \$/kWh) and repeats it for every time step in your optimization horizon.
When you configure a sensor that only provides a present value, that value is used for all optimization periods.

!!! tip "Historical Fallback for Load Sensors"

    For [Load elements](elements/load.md), HAEO can automatically build a forecast from historical recorder data when the sensor lacks a `forecast` attribute.
    Instead of repeating the current value, HAEO fetches past hourly statistics and shifts them forward to predict future consumption.
    Configure this with the `history_days` setting on the Load element.

## Forecast Sensors

Some sensors provide structured forecast data instead of a simple current value.
HAEO automatically detects and parses forecast attributes from supported integrations.
Custom template sensors that match these formats will also work.

**Supported formats** (see [Supported Forecast Formats](#supported-forecast-formats) for complete details):

- [Amber Electric](https://www.home-assistant.io/integrations/amberelectric/) (electricity pricing)
- [AEMO NEM](https://www.home-assistant.io/integrations/aemo/) (Australian electricity pricing)
- [Solcast Solar](https://github.com/BJReplay/ha-solcast-solar) (solar generation)
- [Open-Meteo Solar Forecast](https://github.com/rany2/ha-open-meteo-solar-forecast) (solar generation)
- HAEO sensors (chain HAEO outputs as inputs to other elements)

**Example**: Amber Electric sensor with pricing forecast:

```yaml
entity_id: sensor.amber_general_price
state: 0.28
attributes:
  forecasts:
    - start_time: '2025-11-10T14:00:00+10:00'
      per_kwh: 0.28
    - start_time: '2025-11-10T14:30:00+10:00'
      per_kwh: 0.32
    - start_time: '2025-11-10T15:00:00+10:00'
      per_kwh: 0.29
```

### Interpolation Behavior

Forecast values are interpolated using trapezoidal integration to compute interval averages.
This means HAEO calculates the average power or price over each optimization period, not just point samples.

For the optimization horizon:

- **Position 0**: Present value at the horizon start time
- **Position 1+**: Average value over each subsequent time interval

This approach accurately represents energy consumption and costs over time.

### Unit Conversion

HAEO automatically converts sensor units to the internal representation used for optimization.
You don't need to create template sensors for unit conversion.

**Power conversions**:

- W (watts) → kW (kilowatts)
- MW (megawatts) → kW (kilowatts)

**Energy conversions**:

- Wh (watt-hours) → kWh (kilowatt-hours)
- MWh (megawatt-hours) → kWh (kilowatt-hours)

**Example**: If your battery sensor reports power in watts (`sensor.battery_power` = 5000 W), HAEO automatically converts this to 5 kW for optimization.

All HAEO output sensors use kilowatts (kW) for power and kilowatt-hours (kWh) for energy, regardless of input sensor units.

## Multiple Sensors

You can provide multiple sensors for any field that accepts sensor(s).
HAEO combines them automatically.

**How combining works**:

- Present values **sum together**
- Forecast series **merge on shared timestamps and sum**
- Result: combined present value + combined forecast series

**Example scenarios**:

**Scenario 1: Two forecast sensors**

```yaml
sensor_1: sensor.solar_rooftop_forecast
# Provides forecast series [...array 1 predictions...]

sensor_2: sensor.solar_ground_forecast
# Provides forecast series [...array 2 predictions...]

# Result: Forecast series (sum of both arrays at each timestamp)
```

**Scenario 2: One forecast sensor, one simple sensor**

```yaml
sensor_1: sensor.solar_array_forecast
# Provides forecast series [...predictions...]

sensor_2: sensor.constant_load
# Provides current value: 1.5 kW

# Result: Forecast series (array predictions) + 1.5 kW at each timestamp
```

This makes it easy to model multiple solar arrays, price components, or load sources without manual calculation.

### Visual Example: Combining Two Solar Arrays

When you configure two solar arrays for a solar element, HAEO sums their forecasts at each timestamp.
This example uses real data from an east-facing and west-facing array:

<div class="grid grid-cols-2 gap-4">

```mermaid
xychart-beta
    title "Separate East/West Forecasts (Today)"
    x-axis "Hour" 0 --> 24
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 35, 195, 381, 556, 682, 722, 688, 625, 794, 1185, 1585, 1990, 2384, 2772, 3156, 3524, 3873, 4208, 4525, 4806, 5054, 5274, 5462, 5620, 5748, 5846, 5906, 5939, 5974, 5991, 5995, 5976, 5925, 5844, 5733, 5590, 5409, 5203, 4958, 4661, 4306, 3894, 3450, 2964, 2460, 1909, 1374, 887, 331, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

```mermaid
xychart-beta
    title "Combined East+West Forecast (Today)"
    x-axis "Hour" 0 --> 24
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 230, 1210, 2238, 3140, 3954, 4638, 5215, 5667, 6261, 6966, 7591, 8189, 8763, 9297, 9804, 10251, 10641, 10993, 11301, 11533, 11699, 11813, 11869, 11871, 11820, 11720, 11555, 11347, 11146, 10906, 10635, 10320, 9955, 9543, 9086, 8585, 8037, 7463, 6849, 6188, 5490, 4772, 4184, 3639, 3048, 2389, 1732, 1115, 407, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

</div>

**Legend**: First chart shows east array (blue) and west array (orange) separately. East array peaks in the morning, west array peaks in the afternoon. Second chart shows their combined output summed at each timestamp.

The combined output provides more consistent generation throughout the day.

## Multiple Forecast Windows

Many integrations provide separate forecasts for different time windows (today, tomorrow, day-after-tomorrow).
Combine them using multiple sensors:

| Field     | Value                                                       |
| --------- | ----------------------------------------------------------- |
| **Power** | sensor.solar_forecast_today, sensor.solar_forecast_tomorrow |

HAEO merges all forecast series on shared timestamps and sums values.
This gives you complete horizon coverage from multiple shorter forecast windows.

### Visual Example: Combining Today and Tomorrow Forecasts

When you provide both today's and tomorrow's forecasts, HAEO seamlessly combines them.
This example shows the north array with different weather conditions each day:

<div class="grid grid-cols-2 gap-4">

```mermaid
xychart-beta
    title "Separate Today/Tomorrow Forecasts"
    x-axis "Hour" 0 --> 48
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 352, 1016, 1332, 1564, 1713, 1793, 1809, 1824, 1930, 2081, 2261, 2460, 2683, 2944, 3222, 3479, 3677, 3831, 3957, 4036, 4103, 4125, 4122, 4121, 4129, 4159, 4178, 4127, 3970, 3736, 3449, 3150, 2865, 2557, 2265, 1985, 1746, 1529, 1322, 1150, 1009, 909, 820, 710, 557, 396, 243, 133, 41, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

```mermaid
xychart-beta
    title "Combined 48-Hour Forecast"
    x-axis "Hour" 0 --> 48
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 352, 1016, 1332, 1564, 1713, 1793, 1809, 1824, 1930, 2081, 2261, 2460, 2683, 2944, 3222, 3479, 3677, 3831, 3957, 4036, 4103, 4125, 4122, 4121, 4129, 4159, 4178, 4127, 3970, 3736, 3449, 3150, 2865, 2557, 2265, 1985, 1746, 1529, 1322, 1150, 1009, 909, 820, 710, 557, 396, 243, 133, 41, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

</div>

**Legend**: First chart shows today's forecast (blue) reaching ~6.8kW peak and tomorrow's forecast (orange) with lower ~4.2kW peak due to cloudier conditions. Second chart shows the seamless combined 48-hour coverage.

Notice how tomorrow's partly cloudy forecast shows lower generation than today's clear-sky conditions.
HAEO uses the actual forecast data for each day rather than assuming identical patterns.

## Forecast Coverage and Cycling

Forecasts don't always cover your entire optimization horizon.
HAEO handles partial coverage automatically through **forecast cycling**.

### How Cycling Works

When forecast data ends before your horizon:

1. **Single sensor values** repeat for the entire horizon (already covered above)
2. **Forecast series** cycle using natural period alignment

**Natural period alignment** means HAEO identifies the pattern duration in your forecast and repeats it intelligently:

- A 6-hour forecast from 2pm-8pm cycles to show the same 2pm-8pm pattern for subsequent days
- A weekly forecast cycles weekly, preserving your full week pattern
- Daily patterns like electricity pricing maintain realistic time-of-day structure

This ensures optimization always uses plausible data rather than assuming zero values or constant prices.

### What You'll See

If your optimization horizon is 48 hours but you only have a 24-hour forecast:

- Hours 0-24: Actual forecast data (interpolated)
- Hours 24-48: First 24 hours repeated with time-of-day alignment

For multi-day forecasts (like a 7-day solar forecast), the full pattern cycles at its natural period.

### Visual Example: 24-Hour Forecast Cycling to 72 Hours

When your horizon exceeds forecast coverage, HAEO cycles the pattern with time-of-day alignment.
This example shows a single 48-hour north-facing solar array forecast extended to 72 hours:

<div class="grid grid-cols-2 gap-4">

```mermaid
xychart-beta
    title "48 Hour Forecast (Today + Tomorrow)"
    x-axis "Hour" 0 --> 48
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 352, 1016, 1332, 1564, 1713, 1793, 1809, 1824, 1930, 2081, 2261, 2460, 2683, 2944, 3222, 3479, 3677, 3831, 3957, 4036, 4103, 4125, 4122, 4121, 4129, 4159, 4178, 4127, 3970, 3736, 3449, 3150, 2865, 2557, 2265, 1985, 1746, 1529, 1322, 1150, 1009, 909, 820, 710, 557, 396, 243, 133, 41, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

```mermaid
xychart-beta
    title "Cycled to 72-Hour Horizon"
    x-axis "Hours" 0 --> 72
    y-axis "Power (W)"
    line [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 352, 1016, 1332, 1564, 1713, 1793, 1809, 1824, 1930, 2081, 2261, 2460, 2683, 2944, 3222, 3479, 3677, 3831, 3957, 4036, 4103, 4125, 4122, 4121, 4129, 4159, 4178, 4127, 3970, 3736, 3449, 3150, 2865, 2557, 2265, 1985, 1746, 1529, 1322, 1150, 1009, 909, 820, 710, 557, 396, 243, 133, 41, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 195, 1015, 1857, 2584, 3272, 3916, 4527, 5042, 5467, 5781, 6006, 6199, 6379, 6525, 6648, 6727, 6768, 6785, 6776, 6727, 6645, 6539, 6407, 6251, 6072, 5874, 5649, 5408, 5172, 4915, 4640, 4344, 4030, 3699, 3353, 2995, 2628, 2260, 1891, 1527, 1184, 878, 734, 675, 588, 480, 358, 228, 76, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
```

</div>

**Legend**: First chart shows the combined 48-hour forecast from today and tomorrow. Second chart shows the same 48 hours repeated starting at hour 48 to fill the 72-hour horizon.

Note how the 48-hour pattern repeats starting at hour 48, maintaining realistic time-of-day generation profiles.

## Supported Forecast Formats

HAEO automatically detects and parses these forecast formats:

| Integration                                                                                        | Domain                      | Use Case                        | Format              |
| -------------------------------------------------------------------------------------------------- | --------------------------- | ------------------------------- | ------------------- |
| [Amber Electric](https://www.home-assistant.io/integrations/amberelectric/)                        | `amberelectric`             | Electricity pricing (Australia) | 30-minute intervals |
| [AEMO NEM](https://www.home-assistant.io/integrations/aemo/)                                       | `aemo`                      | Wholesale pricing (Australia)   | 30-minute intervals |
| HAEO                                                                                               | `haeo`                      | Chain HAEO outputs as inputs    | Variable intervals  |
| [Solcast Solar](https://github.com/BJReplay/ha-solcast-solar)                                      | `solcast_pv_forecast`       | Solar generation                | 30-minute intervals |
| [Open-Meteo Solar Forecast](https://www.home-assistant.io/integrations/open_meteo_solar_forecast/) | `open_meteo_solar_forecast` | Solar generation                | Hourly intervals    |

Format detection is automatic—you don't need to specify the integration type.

## Creating Custom Forecast Sensors

You can create custom forecast sensors using Home Assistant templates.
The forecast must be a list of dictionaries with time and value keys.
Times should be either DateTime objects or ISO8601 compatible strings.
Time strings without a timezone are treated as the local time of Home Assistant instance.

**Example**: Custom load forecast sensor:

```yaml
template:
  - sensor:
      - name: Custom Load Forecast
        state: "{{ states('sensor.current_load') }}"
        unit_of_measurement: kW
        device_class: power
        attributes:
          forecast:
            - time: '{{ (now() + timedelta(hours=1)).isoformat() }}'
              value: 2.5
            - time: '{{ (now() + timedelta(hours=2)).isoformat() }}'
              value: 3.0
            - time: '{{ (now() + timedelta(hours=3)).isoformat() }}'
              value: 2.8
```

**Requirements**:

- `state` must be a numeric value (current reading)
- `unit_of_measurement` must match the element's expected unit (kW for power, \$/kWh for prices)
- `device_class` should be set appropriately (`power`, `monetary`)
- `forecast` attribute must contain timestamp/value pairs

HAEO will detect this as a simple forecast format and extract the data.

## Using Input Numbers for Constants

For constant values that don't change over time (fixed prices, baseline loads, power limits), use [input_number helpers](https://www.home-assistant.io/integrations/input_number/) instead of creating custom sensors.

**Creating an input_number**:

1. Navigate to **Settings** → **Devices & Services** → **Helpers**
2. Click **Create Helper** button
3. Select **Number**
4. Configure:
    - **Name**: Descriptive name (e.g., "Base Load Power", "Fixed Import Price")
    - **Unit of measurement**: Match the element's expected unit (kW, \$/kWh, %, etc.)
    - **Minimum/Maximum**: Set reasonable bounds
    - **Initial value**: Set your desired constant
5. Click **Create**

**Using in HAEO configuration**:

Reference the input_number entity ID anywhere HAEO accepts a sensor:

| Field                       | Value                           |
| --------------------------- | ------------------------------- |
| **Forecast**                | input_number.base_load_power    |
| **Import Price**            | input_number.fixed_import_price |
| **Max Power Source→Target** | input_number.inverter_rating    |

HAEO treats input_number helpers like any other sensor, reading the current value and repeating it across the optimization horizon.

**Benefits**:

- Easy to adjust through Home Assistant UI
- No template sensor configuration required
- Clear, simple configuration
- Can be controlled via automations or scripts

## Troubleshooting

### Sensor Not Found

**Problem**: Error message "Sensors not found or unavailable"

**Solutions**:

- Verify the sensor entity ID exists in Home Assistant
- Check that the sensor is available (not "unavailable" or "unknown")
- Ensure the sensor has been created by its integration

### No Forecast Data

**Problem**: Optimization uses repeated current values instead of forecasts

**Possible causes**:

- Sensor doesn't provide forecast attribute
- Forecast attribute is in an unsupported format
- Forecast data is empty or malformed

**Solutions**:

- Check sensor attributes in Developer Tools → States
- Verify the integration is configured correctly
- Review HAEO logs for format detection warnings

### Incorrect Values

**Problem**: Optimized values don't match expectations

**Check**:

- Sensor units match element configuration (kW vs W, \$ vs cents)
- Multiple sensors are summing correctly (intended behavior?)
- Forecast data quality from the source integration
- Optimization horizon covers the relevant time period

## Best Practices

### Update Frequency

- **Pricing sensors**: Update before each optimization run (typically every 5-30 minutes)
- **Solar forecasts**: Update hourly or when weather changes significantly
- **Load forecasts**: Update based on your usage pattern changes

### Data Resolution

Data resolution is less critical than you might expect because HAEO interpolates all data to match your optimization intervals.
However, higher resolution forecasts improve accuracy:

- Use forecasts with resolution matching or finer than your shortest tier duration
- 1-minute tier 1 intervals work well with 5-minute or finer forecast data
- Longer tier durations (30-60 minutes) can use coarser forecast intervals
- Finer forecast data provides more accurate interpolation results

### Data Quality

- Validate forecast accuracy periodically against actual outcomes
- Use reputable forecast providers with proven track records
- Consider multiple forecast sources for critical elements

## Next Steps

<div class="grid cards" markdown>

- :material-history: **Create a historical load forecast**

    ---

    Build a simple load forecast from past consumption data

    [:material-arrow-right: Historical load forecast](historical-load-forecast.md)

- :material-battery-charging: **Configure your elements**

    ---

    Set up batteries, grids, solar, and loads with sensor references

    [:material-arrow-right: Element configuration](elements/index.md)

- :material-chart-line: **Monitor optimization results**

    ---

    View optimized schedules and actual performance

    [:material-arrow-right: Data updates guide](data-updates.md)

- :material-tools: **Troubleshoot issues**

    ---

    Resolve common problems and error messages

    [:material-arrow-right: Troubleshooting guide](troubleshooting.md)

</div>

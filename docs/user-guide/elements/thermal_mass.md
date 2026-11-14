# Thermal mass

Something that stores heat: a hot water tank, a room, or a concrete slab.
HAEO plans when to heat or cool it so it stays within a comfortable temperature at the lowest cost,
heating ahead of expensive periods and letting it drift when power is dear.

A thermal mass is an advanced element.
Heaters, heat pumps, and air conditioners reach it through [connections](connection.md), and hot water use through a [load](load.md) connected to it.

## Configuration

| Field                                          | Type                                     | Required | Default | Description                                      |
| ---------------------------------------------- | ---------------------------------------- | -------- | ------- | ------------------------------------------------ |
| **[Name](#name)**                              | String                                   | Yes      | -       | Unique identifier for this thermal mass          |
| **[Heat capacity](#heat-capacity)**            | Number                                   | Yes      | -       | Energy to warm it by one degree (kWh/°C)         |
| **[Temperature](#temperature)**                | [sensor](../forecasts-and-sensors.md)    | Yes      | -       | Its temperature now (°C)                         |
| **[Lowest temperature](#temperature-limits)**  | Number                                   | No       | -       | Lowest temperature cooling may bring it to (°C)  |
| **[Highest temperature](#temperature-limits)** | Number                                   | No       | -       | Highest temperature heating may bring it to (°C) |
| **[Minimum temperature](#comfort-band)**       | [sensor(s)](../forecasts-and-sensors.md) | No       | -       | Keep it at or above this temperature (°C)        |
| **[Maximum temperature](#comfort-band)**       | [sensor(s)](../forecasts-and-sensors.md) | No       | -       | Keep it at or below this temperature (°C)        |
| **[Comfort cost](#comfort-band)**              | [sensor(s)](../forecasts-and-sensors.md) | Yes      | 1.0     | Cost of heat outside the band (\$/kWh/h)         |
| **[Ambient temperature](#surroundings)**       | [sensor(s)](../forecasts-and-sensors.md) | Yes      | -       | Temperature around it (°C)                       |
| **[Heat loss](#surroundings)**                 | Number                                   | Yes      | -       | Power lost per degree above ambient (kW/°C)      |

Temperatures are in °C.

## Name

Unique identifier for this thermal mass within your HAEO configuration.

**Examples**: "Hot Water", "Lounge", "Bedroom 1"

## Heat capacity

The energy it takes to warm the mass by one degree.
For water, multiply the volume in litres by 0.00116: a 250 litre tank holds 0.29 kWh/°C.
A room's heat capacity includes its walls, floor, and furniture, and is usually between 1 and 5 kWh/°C for a typical room.

## Temperature

The temperature the mass is at now, usually a sensor.
A tank sensor can read low while the tank is heating; HAEO plans from whatever it reports.

## Temperature limits

Limits on how far heating or cooling may push the temperature, such as a tank thermostat's cut-out.
The surroundings can still take the mass past a limit, since nothing the plan does stops heat leaking in or out.

## Comfort band

The minimum and maximum temperatures to keep, which can change through the day.
HAEO keeps the temperature inside the band unless leaving it costs less than the comfort cost.
A high comfort cost makes the band firm; a low one lets HAEO trade comfort for savings.

## Surroundings

The ambient temperature is the temperature around the mass: the outdoor temperature for a room, or the cupboard or garage for a tank.
Heat loss is how much power the mass loses for each degree it is warmer than its surroundings.

A tank's standby loss is often listed in kWh per day at a given temperature difference.
Divide it by 24 and by that difference: 1.2 kWh/day at 45 °C above ambient is 0.0011 kW/°C.

## Configuration examples

### Hot water tank

| Field                   | Value                   |
| ----------------------- | ----------------------- |
| **Name**                | Hot Water               |
| **Heat capacity**       | 0.29                    |
| **Temperature**         | sensor.tank_temperature |
| **Highest temperature** | 65                      |
| **Minimum temperature** | 45                      |
| **Comfort cost**        | 1.0                     |
| **Ambient temperature** | 20                      |
| **Heat loss**           | 0.0011                  |

Connect the heater with a [connection](connection.md) from the switchboard to the tank, with its power limit and an efficiency of 100% for an element or the heat pump's COP, such as 350%.
Connect a [load](load.md) to the tank with your hot water use forecast in kW of heat.

### Room with an air conditioner

| Field                   | Value                      |
| ----------------------- | -------------------------- |
| **Name**                | Lounge                     |
| **Heat capacity**       | 2.0                        |
| **Temperature**         | sensor.lounge_temperature  |
| **Minimum temperature** | 20                         |
| **Maximum temperature** | 24                         |
| **Comfort cost**        | 0.5                        |
| **Ambient temperature** | sensor.outdoor_temperature |
| **Heat loss**           | 0.15                       |

Heat it with a connection from the air conditioner's supply to the room with the heating COP as its efficiency.
Cool it with a second connection with the cooling efficiency and **Takes energy from the target** turned on.
Rooms that share walls exchange heat through a connection between them with a [conductance](connection.md#level-driven-flow).

## Sensors created

### Sensor summary

| Sensor                                             | Unit | Description                                  |
| -------------------------------------------------- | ---- | -------------------------------------------- |
| [`sensor.{name}_temperature`](#temperature-sensor) | °C   | Planned temperature at each period boundary  |
| [`sensor.{name}_heat_loss`](#heat-loss-sensor)     | kW   | Heat lost to the surroundings in each period |

### Temperature sensor

The planned temperature of the mass, with the forecast in its attributes.

### Heat loss sensor

The heat flowing to the surroundings.
It is negative when the surroundings are warmer and heat flows in.

## Next steps

<div class="grid cards" markdown>

- :material-connection:{ .lg .middle } **Connection configuration**

    ---

    Heat and cool a thermal mass, and couple rooms.

    [:material-arrow-right: Connection guide](connection.md)

- :material-home-lightning-bolt:{ .lg .middle } **Load configuration**

    ---

    Draw hot water from a tank.

    [:material-arrow-right: Load guide](load.md)

- :material-math-integral:{ .lg .middle } **Thermal mass modeling**

    ---

    How a thermal mass maps to the optimization.

    [:material-arrow-right: Thermal mass modeling](../../modeling/device-layer/thermal_mass.md)

</div>

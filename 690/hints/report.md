# Benchmark runs

## add_load_constant run 1: failed

- $.connection.value: expected 'Switchboard', found 'Inverter'

I added "Pool pump" as its own Load in the "Home" hub. It uses a fixed power of 0.8 kW. I reopened it afterwards and the saved value shows 0.8 kW.

Points where I hesitated or slipped:
- **Connection:** I left it on the default, Inverter. I didn't check whether the existing Load connects to the Inverter or the Switchboard. A pool pump could just as well hang off the Switchboard, so this may be wrong.
- **Pressing Enter:** I pressed Enter to pick "Use 0.8 kW as a fixed value", and that submitted the form straight away. It happened to work, but I hadn't confirmed the choice first. I checked the saved value afterwards.
- **Shedding:** I never opened the Shedding section and left it at its defaults.

## add_load_constant run 2: passed


"Pool pump" is now in HAEO as its own Load under the Home hub. It has a fixed 0.8 kW power value, and it shows up with 12 entities. I didn't open the new load to check its settings afterwards. The only confirmation was HAEO's "Created configuration for Pool pump" message and the entry in the hub list.

Points where I hesitated or slipped:
- **Connection choice:** The form offered only Inverter or Switchboard, and it defaulted to Inverter. I picked Switchboard on the assumption that a household load belongs there. I didn't check which one the existing "Load" uses, so that is a guess.
- **Connection dropdown:** My first attempt to change the connection didn't register, so I set the forecast first and came back to it. It showed Switchboard before I submitted.
- **Forecast field:** The forecast box looked like a sensor picker. I had to type 0.8 to get a "Use 0.8 kW as a fixed value" option, and I wasn't sure at first that a constant was allowed.
- **Shedding section:** I left the collapsed "Shedding" section alone.

## add_load_constant run 3: failed

- $.connection.value: expected 'Switchboard', found 'Inverter'

I added "Pool pump" as its own Load in HAEO with a fixed 0.8 kW forecast. After saving, I reopened it and the 0.8 kW value had saved.

**Hesitations and mistakes:**
- **Connection:** I left it on the default, Inverter. I never chose it. The only other option was Switchboard, which may suit a household load better. I didn't change it because I couldn't tell how the existing Load is connected.
- **Pressing Enter:** After typing 0.8 in the Forecast box, I pressed Enter without first checking that the value had registered. That submitted the whole form. It worked, but I only confirmed the value afterwards.
- **Shedding:** I didn't open the Shedding section and left it at its defaults.

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO and connected it to the Inverter. I picked all 32 Forecast.Solar sensors for it: east, north, south and west, with 8 days for each direction (today, tomorrow, day after tomorrow, and 3 to 7 days from now). HAEO confirmed "Created configuration for Solar", and Solar now appears in the hub's list of devices. I didn't open the saved element again to check the sensor list.

Points where I hesitated or was unsure:
- **Filtering to the right sensors:** The forecast picker also listed Solcast and Sigen sensors, which I didn't want. I typed `sensor.energy_production_` to filter the list and used "Add all 32 matches". I assumed that prefix matched only the Forecast.Solar sensors. The matches were 32, which fits 4 directions × 8 days, and I only read the first part of the confirmation list, not all 32 entries.
- **Connection:** The Connection field was already set to Inverter, so I left it. That matches your setup, where the panels feed the inverter.
- **Curtailment:** I didn't open the Curtailment section and left it at its defaults.

## add_solar_forecast_solar run 2: passed


I added a Solar element to HAEO and connected it to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, each with today, tomorrow, the day after tomorrow and days 3 to 7. After I submitted, HAEO showed "Created configuration for Solar", and Solar now appears in the Home hub's element list.

I didn't open the saved Solar element again to check the stored sensor list. I only confirmed the forecast list in the form before submitting, and I only read the first few entries on the screen. The "Add all 32 matches" option put in every sensor the filter matched.

Points where I hesitated or was unsure:
- **Sensor filter:** I typed `sensor.energy_production_` to select the sensors in bulk. I assumed that matched only Forecast.Solar sensors. The Solcast and Sigen sensors were excluded, and the 32 matches were exactly 4 directions × 8 days.
- **Connection:** The form already had Inverter selected, so I left it. That fits the task, since the panels feed the inverter.
- **Curtailment:** I didn't open the Curtailment section and left it at its defaults.

## add_solar_forecast_solar run 3: passed


Solar is now added to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors. That is 8 for each of east, north, south and west. For each direction there is today, tomorrow, the day after tomorrow and 3 to 7 days from now. I reopened the saved Solar entry and counted 32 forecast entries. None of them were Solcast or Sigen sensors.

Points where I hesitated or made a mistake:
- **Enter submitted the form:** I typed `energy_production_` to filter the list and pressed Enter. I expected it to add the matches, but it added them and submitted the whole form in one go. I hadn't meant to submit yet, so I checked the saved result afterwards, and it was correct.
- **Selection not checked first:** I didn't look at what the filter had selected before submitting, so I didn't know the list was right until I reopened the entry.
- **Odd sensor names:** The south sensors are named "South solar prediction forecast" rather than "production". The entity IDs matched the pattern, so I included them as Forecast.Solar sensors.
- **Connection and curtailment:** The Connection field already said Inverter, and I accepted that without comparing it to the Switchboard. I didn't open or change the Curtailment section.

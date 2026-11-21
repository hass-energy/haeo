# Benchmark runs

## add_solar_forecast_solar run 1: passed


I added a Solar element to the Home hub with all 32 Forecast.Solar sensors. Home Assistant showed "Created configuration for Solar", and Solar now appears in the hub's device list. I didn't open the new Solar entry afterwards to check its saved settings.

- **Sensors:** each of the four directions (east, north, south, west) has eight sensors, covering today, tomorrow, the day after tomorrow, and 3 to 7 days from now. The picker's "Select all 32" option picked them all up when I searched for `energy_production`.
- **Connection:** I left it on the default, Inverter (DC), because the panels feed into the inverter.
- **Other fields:** I left the optional Curtailment section untouched.

Points where I hesitated or made a mistake:
- **Picking sensors:** my first click selected a single sensor (East, 3 days from now), and the dropdown closed after it. I then searched `energy_production` and used "Select all 32", which covered every sensor.
- **Sensor names:** the south sensors are labelled "solar prediction forecast" while the others say "solar production forecast". They share the same `energy_production_*` entity names, so I counted them as Forecast.Solar sensors.
- **Other forecasts:** I did not select the Solcast PV forecast sensors that also appeared in the list, since they aren't Forecast.Solar.

## add_solar_forecast_solar run 2: passed


I added Solar to HAEO, connected to the Inverter, with all 32 Forecast.Solar sensors. That is east, north, south and west, each with today, tomorrow, day after tomorrow and 3 to 7 days from now. HAEO showed "Created configuration for Solar", but I didn't reopen the Solar entry afterwards to check the saved sensors.

I used "Select all 32" in the picker after typing `energy_production_` into the search box. The picker also listed Solcast and Sigen sensors, which I left out because you asked for Forecast.Solar only.

Points where I hesitated or went off track:
- **Connection:** The form already had Inverter selected, and I kept it. You said the panels feed into your inverter, so that matched.
- **Picker closing:** Clicking a single sensor closed the list, so picking them one by one would have been slow. I switched to the search box and "Select all".
- **Curtailment:** I left the optional Curtailment section alone.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub, connected to the Inverter (DC). It uses all 32 Forecast.Solar energy production sensors: east, north, south and west, with 8 sensors each. I used the picker's "Select all 32" option and checked that all 32 were listed before I submitted. HAEO showed "Created configuration for Solar." I only checked the Solar entry by counting "Solar" on the page afterwards, and I didn't open it to review its settings.

Points where I hesitated or slipped:
- **Connection:** I left the default (Inverter, DC) without changing it. You said the panels feed into the inverter, so I believe it's right.
- **Sensor choice:** I wasn't sure whether to include the day-ahead sensors (today, tomorrow, day after tomorrow, and 3 to 7 days from now) as well as today's. Your request said "every day it covers", so I included them all.
- **Picker behaviour:** The picker closed after I picked the first sensor, so I had selected one sensor before I noticed "Select all 32". Searching "energy_production_" brought up the "Select all 32" option, and the other forecast sensors (Solcast, Sigen) were not in that list.
- **Curtailment:** I didn't open the Curtailment section, and I didn't check the finished entry afterwards.

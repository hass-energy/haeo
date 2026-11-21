# Benchmark runs

## add_load_constant run 1: passed


The "Pool pump" load is added to the Home hub. It runs at a fixed 0.8 kW, and the Home hub now lists a "Pool pump" Load device with 12 entities.

Where I hesitated or was unsure:

- **Connection choice:** The form defaulted to Inverter. I changed it to Switchboard because the pump is an AC house load on the household mains, not something fed through the inverter. I did not check how the existing "Load" element is connected, so this is my judgement rather than a confirmed match with your setup.
- **Constant value:** The Forecast field accepts a typed number as a fixed value. I typed 0.8 and picked "Use 0.8 kW as a fixed value", and the field then showed "0.8 kW". I did not confirm the saved value after submitting.
- **Shedding:** I left the optional Shedding section alone. You said the pump runs all the time, so I did not set it to be sheddable, but I did not read what that section does.
- **Mistake:** I did not run any check on the load's saved configuration or entities beyond the success message and the device appearing in the list.

## add_load_constant run 2: passed


I added "Pool pump" to the Home hub as a regular Load with a fixed 0.8 kW forecast. HAEO confirmed "Created configuration for Pool pump", and a Pool pump Load device with 12 entities now appears under Home.

Settings:
- **Name:** Pool pump
- **Connection:** Switchboard
- **Forecast:** fixed value 0.8 kW (entered as a number, shown as kW)
- **Shedding:** left unset

I did not reopen the saved entry to check that 0.8 kW was stored. I only saw it in the form before submitting.

Points where I hesitated or may have gone wrong:
- **Load vs. Deferrable load:** I chose Load because the pump runs constantly at a steady draw and doesn't need to be scheduled. A deferrable load would be the choice if it could be shifted in time.
- **Connection:** I picked Switchboard because the pump is an AC house appliance. The default was Inverter, and I didn't check which connection the existing "Load" entry uses, so this may not match your setup.
- **Units:** The fixed value field showed "kW" next to the number, so I took 0.8 as kW, which matches your 0.8 kW figure.
- **Shedding:** I skipped it because the task didn't mention shedding. If the pump can be switched off when power is short, that setting would need adding.

## add_load_constant run 3: passed


I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW forecast. The Home hub now lists a Pool pump device with 12 entities, and the success dialog confirmed "Created configuration for Pool pump."

Points where I hesitated or was unsure:

- **Connection:** The default was Inverter. I changed it to Switchboard because a pool pump is a house-side AC load and I took the Switchboard to be the house bus. I didn't open the existing Load to compare its connection, so this is my best judgement rather than a checked match.
- **Fixed value:** The form offered "Type a number to use it as a fixed value," and it showed the unit as kW. I entered 0.8 and left it as kW, which matches your 0.8 kW figure.
- **Shedding:** I left this section at its default because you said the pump runs all the time. I did not check whether any shedding setting would be sensible for it.
- **Verification:** I confirmed the entity count and the device's presence on the hub page. I did not open the new load to read back its saved values.

## add_solar_forecast_solar run 1: passed


The Solar element is added to HAEO under the Home hub, connected to the Inverter, with all 32 Forecast.Solar sensors as its forecast: the today, tomorrow and day-after-tomorrow sensors plus the 3 to 7 days-from-now sensors, for each of east, north, south and west.

I didn't open the new Solar element afterwards to check its configuration. The success dialog confirmed creation and the hub now shows a Solar device with 4 entities.

Points where I hesitated or was unsure:

- **Sensor filter:** I typed "energy_production" in the forecast picker, which returned exactly 32 matches ("Add all 32 matches"). I added them all and confirmed in the saved output that all 32 were listed. I left out the Solcast, Sigen and other sensors in the list because they aren't Forecast.Solar.
- **South sensor naming:** The south sensors are labelled "South solar prediction forecast" while the other directions say "solar production forecast". I included them because their entity IDs follow the same `energy_production_*_south` pattern as the others, but I couldn't confirm they come from the same Forecast.Solar source.
- **"Today" sensors:** The today sensors are partial-day figures. I kept them because you asked for every day the integration covers, but HAEO may treat them differently from full future days.
- **Connection:** It defaulted to Inverter. I kept it because you said the panels feed the inverter, though I didn't check the Switchboard option against your wiring.
- **Name and curtailment:** I left the name as "Solar" and the Curtailment section at its defaults, since you gave no guidance on either.

## add_solar_forecast_solar run 2: passed


I added the solar hub named "Solar" to HAEO, connected to the Inverter, with all 32 Forecast.Solar production sensors. The success dialog said "Created configuration for Solar," and the Home hub now lists Solar with 4 entities.

- **Sensors:** I typed "energy_production" in the Forecast picker and used "Add all 32 matches." That is 4 directions (east, north, south, west) × 8 days (today, tomorrow, day after tomorrow, and 3 to 7 days from now). I checked the first part of the saved list against the picker and it matched.
- **Connection:** left at Inverter, since the panels feed the inverter.
- **Name:** left as the default "Solar".
- **Curtailment:** left at its default; I did not open it.

Points where I hesitated or was unsure:
- **South sensors:** the four south sensors are labelled "South solar prediction forecast", while the others say "solar production forecast". Their entity IDs use the same `energy_production_*_south` pattern, so I included them. I did not check the source integration of any of the sensors.
- **Day coverage:** I took the eight days the picker offered rather than checking how far the Forecast.Solar integration actually reaches.
- **Verification:** I confirmed the hub was created and that its 4 entities are present, but I did not open the Solar hub afterwards to check the saved forecast list in full.
- **Tool use:** one attempt to grep a saved tool-output file was denied by the permission mode. I read the file with the Read tool instead; I did not try to get around the denial.

## add_solar_forecast_solar run 3: passed


I added the Solar element to the Home hub with all 32 Forecast.Solar sensors, and the setup reported "Created configuration for Solar." The Solar device now appears under Home with 4 entities.

**What I set up**
- **Name:** Solar (the default).
- **Connection:** Inverter (the default, which is correct because the panels feed the inverter).
- **Forecast:** 8 sensors per direction for east, north, south and west, covering today, tomorrow, day after tomorrow, and 3 to 7 days from now. That gives 32 in total.
- **Curtailment:** left at its default.

**Where I hesitated or made a mistake**
- I typed `energy_production` into the forecast picker and used "Add all 32 matches." I checked the resulting list against the expected 8-per-direction pattern, but I did not confirm after submitting what was saved.
- The South sensors are named "South solar prediction forecast" while the others say "production." I included them because their entity IDs follow the same `sensor.energy_production_*_south` pattern as the rest. If that is wrong, the South group needs a second look.
- The picker also listed Solcast PV Forecast sensors. I left them out because Solcast is a different integration from Forecast.Solar.
- I could not grep the saved output file because Bash was denied in that step. I read the file with the Read tool instead and got the same information.
- I did not change the default Curtailment settings, because the task did not mention curtailment and I do not know whether it applies to your system.

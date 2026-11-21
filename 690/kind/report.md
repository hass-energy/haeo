# Benchmark runs

## add_battery run 1: passed


I added the Battery to your Home hub, and it now shows up as a device with 21 entities. I didn't open the battery's settings afterwards to re-read them.

- **Connection:** Inverter (DC). That was already selected, and I kept it because the battery is connected through your inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (currently 12.8%).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** 5%, entered as a fixed value.
- **Left alone:** I kept the default name "Battery" and left the pricing, efficiency and advanced settings at their defaults.

Points where I hesitated:
- I wasn't sure the Inverter connection was right until I compared it with the Switchboard option. It lists Grid, Inverter and Load, so it looks like the AC side.
- The charging-power search also listed the discharging-power sensor. I picked each sensor by its exact name.
- The "5" I typed for the minimum charge level had to be picked from a dropdown as "Fixed value 5 %". It showed as 5 % afterwards.
- The battery's current charge is 12.8%, which is above the 5% floor, so the limit doesn't conflict with it.

## add_battery run 2: passed


I added the battery to HAEO, and the dialog confirmed "Created configuration for Battery." I didn't reopen it afterwards to check the saved values.

- **Connection:** Inverter (DC). I left the default, since the battery is connected through your inverter.
- **Capacity:** the Sigen Plant Rated Energy Capacity sensor.
- **State of charge:** the Sigen Plant Battery State of Charge sensor.
- **Min charge level:** a fixed 5%.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor.

I left the other fields at their defaults: max charge level, pricing, efficiency and advanced settings.

Points where I hesitated or slipped:
- The max charge power picker showed a "Select all 2" option with both power sensors. I clicked the individual Charging Power sensor instead, and did the same for discharging.
- The name stayed as the default "Battery". You didn't give one, so I didn't change it.
- I didn't check the efficiency and advanced sections.

## add_battery run 3: passed


I added the battery to the Home hub as "Battery". HAEO's success dialog said it created the configuration, and the hub now lists Battery with 21 entities. I didn't reopen the saved battery to check the fields.

- **Connection:** Inverter (DC), the default.
- **Capacity:** Sigen Plant Rated Energy Capacity, which reads 32.24 kWh.
- **State of charge:** Sigen Plant Battery State of Charge, which reads 12.8 %.
- **Max charge power:** Sigen Plant ESS Rated Charging Power, which reads 16.8 kW.
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power, which reads 19.2 kW.
- **Min charge level:** fixed 5 %, so it is never discharged below that.

I left max charge level, pricing, efficiency and advanced settings at their defaults.

Points where I hesitated or slipped:
- I accepted the default Inverter (DC) connection without comparing it to Switchboard (AC). A Sigenergy battery behind the inverter seemed to fit DC.
- When I searched for the charging power sensor, the picker offered a "Select all 2" option. I clicked the specific sensor instead.
- A screenshot confirmed the power sensors and the 5 % level were selected before I submitted. I never saw the capacity and state-of-charge fields on screen, so I'm relying on the picker clicks for those.
- One command was denied by the sandbox, so I switched to a screenshot to check the form.

## add_battery_raw run 1: passed


I added the Battery to the Home hub. HAEO showed "Created configuration for Battery", but I didn't reopen the entry afterwards to check the saved values.

- **Connection:** the Inverter option, labelled "DC". It was already selected by default and fits a battery on your inverter, so I left it.
- **Capacity:** Sigen Plant Rated Energy Capacity (`sensor.sigen_plant_rated_energy_capacity`, 32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (`sensor.sigen_plant_battery_state_of_charge`, 12.8%).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (`sensor.sigen_plant_ess_rated_charging_power`, 16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (`sensor.sigen_plant_ess_rated_discharging_power`, 19.2 kW).
- **Min charge level:** fixed at 5%, so it never discharges below that.

I left max charge level, pricing, efficiency and the advanced options at their defaults.

Points where I hesitated or was unsure:
- I wasn't sure whether to use the Inverter or Switchboard connection. I picked the Inverter because you said the battery is connected through it.
- The max charge power search showed a "Select all 2" option next to the sensor, which suggests more than one match. I clicked the specific Rated Charging Power sensor rather than "Select all".
- To set 5% I typed "5" and chose the "Fixed value 5 %" option. Before submitting I confirmed it showed as a fixed value.
- I didn't change the default charge cost of -0.001 $/kWh. You didn't mention pricing, so I left it.

## add_battery_raw run 2: passed


I added the battery to HAEO as "Battery" on the Inverter connection. HAEO showed "Created configuration for Battery", and Battery appears in the Home hub's list afterwards. I did not open the new Battery entry to re-check its saved values.

- **Size:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **Current charge:** Sigen Plant Battery State of Charge (12.8%).
- **Minimum charge level:** a fixed 5%, so it should never discharge below that.
- **Maximum charging power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Maximum discharging power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).

I left everything else at its default, including max charge level, pricing, efficiency and advanced settings.

Points where I hesitated or slipped:
- **Connection:** The form defaulted to "Inverter, DC", which matches a battery connected through the inverter, so I kept it without checking anything else.
- **Power sensors:** The charging-power search offered a "Select all 2" option next to the two sensors. I clicked only the single charging sensor, and did the same for discharging.
- **Search results:** My first search for the capacity sensor returned only one match, so there was no ambiguity.

## add_battery_raw run 3: passed


I added the Sigenergy battery to HAEO as "Battery". The dialog showed "Created configuration for Battery", and a Battery entry now appears under Home. I didn't reopen the entry to re-check the saved values.

- **Connection:** Inverter (DC), which was the default. It matches a battery that connects through your inverter.
- **Capacity:** the Sigen Plant Rated Energy Capacity sensor, which read 32.24 kWh.
- **Current charge:** the Sigen Plant Battery State of Charge sensor, which read 12.8 %.
- **Minimum charge level:** a fixed 5 %, so it should never discharge below that.
- **Maximum charge power:** the Sigen Plant ESS Rated Charging Power sensor, which read 16.8 kW.
- **Maximum discharge power:** the Sigen Plant ESS Rated Discharging Power sensor, which read 19.2 kW.

I left everything else (pricing, efficiency, advanced settings, maximum charge level) at the defaults.

Points where I hesitated or was unsure:
- I left the connection on the default, Inverter (DC). It matched your description, but I didn't check it against any other information.
- The pricing fields came pre-filled, for example a charge cost of -0.001 $/kWh. I left them alone, since you didn't mention them.
- Each sensor search returned a single sensor, apart from the charging-power search, which also showed a "Select all 2" option. I picked the named sensor each time.
- When I started, the charge-level field showed 5 % only as a suggestion. I clicked it to make it a fixed value, and it then appeared as a "Fixed value 5 %" chip.

## add_connection_raw run 1: passed


I added a connection called "Inverter to Switchboard" to the Home hub, running from Inverter to Switchboard with Max power set to a fixed 10 kW. It now shows in the hub's device list as a Connection with 2 entities. I didn't open it again to re-check the saved values.

I left Price and Connection efficiency empty because you didn't give values for them.

Points where I hesitated or slipped:
- **Endpoints:** The form already had Inverter as source and Switchboard as target, so I left them. I didn't confirm that the pre-filled direction was right beyond reading the two fields.
- **Max power field:** It wasn't obvious whether typing "10" would be read as kW. The dropdown showed "Fixed value 10 kW", so I picked that.
- **Connection name:** The name was my choice, since you didn't specify one.
- **Status update:** I was slow to give you an update partway through.

## add_connection_raw run 2: passed


I added a connection called "Inverter to Switchboard" to the Home hub. It runs from the Inverter to the Switchboard with max power set to a fixed 10 kW. It now shows in the hub's device list with 2 entities.

I only checked that it appeared in the list. I didn't open it again to confirm the 10 kW saved.

Points where I hesitated or went beyond the instructions:
- The form already had Inverter as the source and Switchboard as the target, so I left both unchanged.
- I chose the name "Inverter to Switchboard" myself. The form's default was just "Connection", and you didn't specify a name.
- I left the Price and Connection efficiency fields at their defaults, since you only asked for the limit.
- The max power box offered "Fixed value 10 kW" as an option rather than taking the typed number directly, so I clicked that option.

## add_connection_raw run 3: passed


I added a connection named "Inverter to Switchboard" to the Home hub. It runs from the Inverter to the Switchboard, with Max power set to a fixed 10 kW. After I submitted, HAEO showed "Created configuration for Inverter to Switchboard." The connection now appears in the hub's device list with 2 entities.

I didn't reopen the connection to check the saved limit. I only saw the 10 kW value in the form before I submitted it.

I left Price and Connection efficiency at their defaults, since you only gave a power limit.

Points where I hesitated or slipped:
- **Endpoints:** The form already had Inverter as source and Switchboard as target, so I didn't change them. I only checked that this matched the direction you asked for.
- **Name:** You didn't give a name, so I chose "Inverter to Switchboard".
- **Max power entry:** Typing "10" only offered a "Fixed value 10 kW" option, which I had to click to confirm it.
- **Status update:** I went quiet for a while before the last steps, and you had to prompt me for an update.

## add_grid_amber run 1: passed


The Grid is now added to Home. HAEO showed "Created configuration for Grid", and Grid appears in the hub's list of parts.

- **Connection:** Switchboard (AC). It was already selected by default, and I left it because the Switchboard is where the grid meets the Inverter and Load.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I didn't reopen the Grid's settings to check the saved values; I relied on the confirmation message.

Points where I hesitated or made mistakes:
- **Connection:** I wasn't certain Switchboard was the right place for the grid, since the form offered Inverter (DC) as well. I picked Switchboard because it was the default.
- **Limits:** Both limits started at 100 kW. I removed those values and typed in mine.
- **Wasted step:** After clicking the Import limit box, the page printed so much that I had to re-read it with a filter.

## add_grid_amber run 2: passed


I added the Grid to HAEO and got a "Created configuration for Grid" confirmation. I didn't reopen it afterwards to check the saved values.

- **Connection:** Switchboard (AC). It was already selected, so I left it.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW, a fixed value.
- **Export limit:** 30 kW, a fixed value.

Points where I hesitated or made a mistake:
- **Connection:** I wasn't sure Switchboard was the right place for the grid. I kept the default because the Switchboard is the AC junction that the Inverter and Load already hang off.
- **Power limits:** The import and export limits both defaulted to 100 kW. I removed each and typed the new value, since I wasn't sure typing would replace the default.
- **Import limit entry:** I didn't confirm the 55 was accepted before moving on. The next screen showed it as a fixed 55 kW, so it worked.

## add_grid_amber run 3: passed


I added the Grid to your HAEO "Home" setup. HAEO showed "Created configuration for Grid." I didn't re-open the Grid afterwards to check the saved values.

- **Connection:** Switchboard (AC). It was already selected by default, and I left it because the Switchboard is where the grid connects.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

Points where I hesitated or made a mistake:
- The Switchboard default was unexplained, so I assumed it was right rather than confirming it.
- Both power limits started at 100 kW, so I removed those values and typed in 55 and 30. The field had no obvious way to overwrite a value.
- When I removed the 100 kW import value, the picker opened a very long list of unrelated sensors, which made the page output hard to read. It didn't affect the result.

## add_load_constant run 1: passed


I added "Pool pump" to the Home hub as its own Load, with a fixed 0.8 kW power. It now shows up in the hub's list of parts.

I connected it to the Switchboard (AC). That was already selected by default, and I kept it because a pool pump is a mains-powered appliance.

Points where I hesitated:
- **Connection:** I wasn't told where the pump plugs in. I assumed the Switchboard rather than the Inverter (DC).
- **Constant value:** The "Forecast" field is required. I wasn't sure a plain number would work, but typing 0.8 offered a "Fixed value 0.8 kW" option, so I picked that.
- **Shedding:** I left the collapsed "Shedding" section alone, since you said the pump runs all the time.

## add_load_constant run 2: passed


I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW power value. It's connected to the Switchboard, and it now shows up in the hub's device list.

I did not open the new entry afterwards to check its saved settings.

Points where I hesitated:
- **Connection:** I left the default, Switchboard (AC), because a household pump plugs into the house wiring. I didn't have a strong reason to change it.
- **Fixed value:** In the Forecast field I typed "0.8" and picked the "Fixed value 0.8 kW" option, since I wasn't sure a plain number would be accepted. I assumed that option means a constant 0.8 kW at all times.
- **Shedding:** I skipped the "Shedding" section. The pump runs all the time, so I didn't set anything there.

## add_load_constant run 3: passed


I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW forecast, connected to the Switchboard. HAEO showed "Created configuration for Pool pump", and the new load appears in the hub's list.

Points where I hesitated:
- **Connection:** I left the default, Switchboard (AC), without confirming it. I assumed the pump is wired to your household AC supply, not to the inverter's DC side.
- **Shedding:** I left this section collapsed and unchanged. The pump runs all the time, so I didn't set any shedding.

## add_load_forecast run 1: passed


I added a Load called "Household" to your Home hub. It's connected to the Switchboard and uses both Sigenergy sensors:
- **Forecast:** Sigen Plant Consumed Power Forecast
- **Current value:** Sigen Plant Consumed Power

HAEO showed "Created configuration for Household". The Household device now appears under the hub, and the entity count went from 49 to 61.

I didn't open the new load afterwards to check which sensors it saved. I only saw both sensors listed as selected before I submitted.

Points where I hesitated or was unsure:
- **Name:** I changed the default "Load" to "Household". You didn't give a name, so that was my choice.
- **Connection:** I kept the default, Switchboard. You didn't say where the load connects, and household consumption seemed to belong on the switchboard.
- **One field for both sensors:** The Forecast field accepts several sensors. I wasn't sure the current-value sensor belonged there, so I added it to the same field. There was no other field for it.
- **Dropdown closing:** After my first pick, the dropdown closed. I searched "consumed" to find the second sensor, which cost a few extra steps.

## add_load_forecast run 2: passed


I added a load to the Home hub, connected to the Switchboard. It uses both Sigen sensors: Sigen Plant Consumed Power for the current value and Sigen Plant Consumed Power Forecast for the forecast. After I submitted it, the load showed up on the HAEO page with 12 entities. I didn't open those entities to check their values.

Points where I hesitated or was unsure:
- **Name:** I left the default name "Load" instead of something like "Household", which may not be the clearest label.
- **Connection:** The Switchboard was already selected by default. I kept it because household consumption is an AC load, but the form didn't say so.
- **Sensor field:** The "Forecast" field accepted several sensors, and its list also offered solar forecast sensors. I assumed that adding the current-value sensor alongside the forecast one was the intended way to use both.
- **Shedding section:** I didn't open the optional "Shedding" section or change it.

## add_load_forecast run 3: passed


I added a load called "Household" to your Home hub. HAEO confirmed it with "Created configuration for Household", and it now shows in the device list.

- **Connection:** the Switchboard, which was already selected by default. I assumed that's right for whole-house consumption.
- **Forecast sources:** `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power`. Both went into the one "Forecast" field, which accepts several sensors.

I didn't check the load's values or the optimizer's output afterwards. I only confirmed that the new load appears in the list.

Points where I hesitated:
- **Current-power sensor:** the form has no separate field for it, only the one "Forecast" picker. I put it in the same field, though I'm not certain HAEO combines the two the way I expect.
- **Name:** I renamed the default "Load" to "Household". That was my choice, not something you asked for.
- **Skipped section:** I left the "Shedding" section alone because you didn't mention it.

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO and connected it to the Inverter. Its forecast uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 days for each direction. HAEO showed "Created configuration for Solar", and Solar now appears under Home.

I opened the Solar form from the HAEO page. I searched the forecast picker for `energy_production`, which matched exactly those 32 sensors, and used "Select all". After that, the form showed 32 removable entries.

I did not open the new Solar element again to check the saved values.

Points where I hesitated or was unsure:
- **Connection:** the form already had Inverter selected, and I kept it because your panels feed into the inverter. I didn't test the Switchboard option.
- **Day coverage:** I included every day sensor the picker offered (today, tomorrow, the day after, and 3 to 7 days out), since you said all of them.
- **Verification:** I confirmed the 32 entries before submitting and saw the success message afterwards.

## add_solar_forecast_solar run 2: passed


I added a Solar element to the Home hub and selected all 32 Forecast.Solar sensors for it. That is 8 per direction (east, north, south, west). The 8 are today, tomorrow, the day after tomorrow, and 3 to 7 days from now.

HAEO showed "Created configuration for Solar", and Solar now appears under the Home hub. I didn't open the saved Solar entry again to check the sensors one by one.

I connected it to the Inverter, which was already selected. The other choice was the Switchboard. I assumed the Inverter was right because you said the panels feed into it. I left the Curtailment section untouched.

Points where I hesitated or was unsure:
- **Excluding other sensors:** the picker listed 41 sensors, including Sigen Plant and Solcast ones. I typed "energy_production" to filter to the 32 Forecast.Solar sensors before using "Select all".
- **South sensor names:** the south sensors are labelled "solar prediction forecast" rather than "solar production forecast". They share the same `energy_production_*_south` entity IDs as the other directions, so I treated them as Forecast.Solar.
- **Connection:** as above, I kept the pre-selected Inverter connection on the assumption that it matches your setup.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub and used all 32 Forecast.Solar sensors as its forecast. That is 8 per direction (east, north, south, west). Per direction, the 8 are today, tomorrow, day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open it again to check the saved settings.

- **Connection:** I left it on Inverter (DC), which was already selected. I didn't change it, because your panels feed into the inverter.
- **Forecast sensors:** I typed "energy_production" into the picker and used "Select all". That filtered the list to 32 sensors, and the other solar sensors in the list (Solcast and the Sigen plant ones) were left out. I checked the 32 selected entries before submitting.

Points where I hesitated or slipped:
- **Connection choice:** I briefly considered whether Switchboard (AC) might fit better. I stayed with Inverter because the form's default matched what you described.
- **Truncated output:** My first search attempt piped the output to `head`, which cut it off and raised a harmless BrokenPipe error. I re-ran it to see the results.
- **Final check:** I only searched for "Solar" in the page text afterwards. That shows the element was created, not that the 32 sensors were stored.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub and connected it to the Inverter. It uses all three Solcast forecast sensors: Today, Tomorrow and Day 3. After I submitted it, Solar appeared in the hub's list with 4 entities. I didn't open it again to check the saved settings.

I left the Curtailment section alone.

Points where I hesitated or slipped:
- **Connection:** the Inverter option was already selected, which matches your setup, so I kept it. The other choice was the Switchboard.
- **Forecast picker:** it let me pick only one sensor at a time. I had to search "solcast" and click each of the three separately.
- **Missed progress update:** I went quiet for a few steps near the end, until the "say what you're doing" prompt.

## add_solar_solcast run 2: passed


I added a Solar element to HAEO and confirmed it. It connects to the Inverter and uses the three Solcast PV Forecast sensors (Today, Tomorrow and Day 3) as its forecast.

HAEO showed "Created configuration for Solar", and Solar now appears in the Home hub's element list. I didn't look at the solar entities or any optimizer output, so I haven't checked that the forecast values come through.

Points where I hesitated or slipped:
- **Connection default:** "Inverter" was already selected for Connection, and I kept it. Your panels feed the inverter, so it matched, but I didn't open the Switchboard option to compare.
- **Forecast picker:** It closed after each pick, so I had to search "solcast" again for each sensor. I checked after each pick that the sensor had been added.
- **Look-alike sensors:** The list also had many "Estimated energy production" sensors (East, North, South, West) and Sigen Plant sensors. I ignored them because you named Solcast.
- **Curtailment:** I left this section collapsed and unchanged because you didn't mention it.

## add_solar_solcast run 3: passed


I've added the Solar element to HAEO. It connects to the Inverter (DC) and uses all three Solcast forecast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. The dialog said "Created configuration for Solar", and Solar now shows up in the Home hub's device list.

I didn't check the new Solar device's entities or run an optimization.

Points where I hesitated or was unsure:
- **Connection:** The form already had Inverter selected, which matches your panels feeding the inverter, so I left it.
- **Forecast picker:** It closed after each pick, so I had to reopen it twice (searching "solcast") to add the other two sensors. I checked that all three showed as selected before submitting.
- **Other forecast sensors:** The list also had many unrelated `energy_production_*` sensors (East, North, South, West). I ignored them because you asked for Solcast.
- **Curtailment:** I didn't open that section and left it at its defaults.

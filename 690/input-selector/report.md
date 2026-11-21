# Benchmark runs

## add_battery run 1: passed


I added the Sigenergy battery to HAEO. The form accepted it with a "Created configuration for Sigenergy Battery" message. I didn't reopen the entry afterwards to check the saved values.

- **Name:** Sigenergy Battery.
- **Connection:** Inverter, which was the default. You said the battery connects through your inverter, so I left it.
- **Capacity:** Sigen Plant Rated Energy Capacity.
- **State of charge:** Sigen Plant Battery State of Charge.
- **Max charge power:** Sigen Plant ESS Rated Charging Power.
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power.
- **Min charge level:** 5% as a fixed value.

I left the pricing and efficiency settings at their defaults.

Points where I hesitated or made a mistake:
- **Name:** I changed the default name "Battery" to "Sigenergy Battery". You didn't ask for that.
- **Min charge level:** the field only listed the state of charge sensor at first, so I wasn't sure a fixed number was allowed. Typing 5 offered "Use 5 % as a fixed value", which I picked.
- **Max charge power search:** the max charge power picker listed many unrelated sensors. I scrolled through them to find the right one.

## add_battery run 2: passed


I added the battery to HAEO as "Sigenergy Battery", and HAEO confirmed it created the configuration. I didn't re-open the saved battery afterwards to check the stored values.

- **Connection:** Inverter. I left it at the default, since you said the battery connects through your inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8%).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** a fixed 5%.
- **Everything else:** the pricing and efficiency fields are left at their defaults.

Points where I hesitated or made a mistake:
- **Min charge level:** the field looked like a sensor-only picker and offered only the state-of-charge sensor. I typed "5", and it offered "Use 5 % as a fixed value", which I chose.
- **Power sensors:** the power pickers listed many unrelated sensors, so I searched for "rated charging" and "rated discharging" to find the right ones.
- **Name:** I changed the default name "Battery" to "Sigenergy Battery". You didn't ask for that.

## add_battery run 3: passed


I added the Battery to HAEO and connected it to the Inverter. HAEO showed "Created configuration for Battery", and I clicked Finish. I didn't reopen the Battery afterwards to re-check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor (32.24 kWh).
- **State of charge:** the Sigen Plant Battery State of Charge sensor (12.8% at the time).
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor (16.8 kW).
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor (19.2 kW).
- **Minimum charge level:** a fixed value of 5%.

I left the other fields as they were, including the pricing fields, Max charge level and the efficiency and advanced settings.

Points where I hesitated or went wrong:
- **Min charge level:** the picker offered only the state of charge sensor at first and had no obvious place for a plain number. I typed "5" and chose "Use 5 % as a fixed value", and the field then showed a fixed value of 5.
- **Max charge power:** I opened the picker and got a long list of unrelated solar forecast sensors. I typed "rated charging" to filter it, and the right sensor appeared. I did the same for discharging power.
- **Connection:** I assumed the default "Inverter" was right because you said the battery connects through your inverter. I didn't check the other option, Switchboard.

## add_grid_amber run 1: passed


I added the Grid to HAEO, and it now appears under the Home hub with 12 entities.

- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.
- **Connection:** Switchboard.

I confirmed the success message and the new Grid entry on the integration page. I didn't open the Grid again to re-read the saved values.

Points where I hesitated or made a mistake:
- **Connection choice:** The form defaulted to Inverter. You didn't say where the grid connects, so I chose Switchboard because a grid supply normally feeds the switchboard. If your grid actually connects through the inverter, this needs changing.
- **Dropdown mistake:** I opened the Connection dropdown, then clicked the price field, which closed it without selecting anything. I noticed the Connection still said Inverter and set it to Switchboard afterwards.
- **Price fields:** Both price fields accepted multiple sensors and listed both Amber sensors in each. I wasn't sure whether to expect that. I picked exactly one for each.
- **Power limits:** The limits were collapsed and defaulted to 100 kW. I opened the section and replaced both values.

## add_grid_amber run 2: passed


I added the Grid to HAEO. HAEO showed "Created configuration for Grid." and I clicked Finish. I didn't reopen the Grid afterwards to check the saved values.

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Limits:** import 55 kW, export 30 kW. Both fields defaulted to 100 kW, and I changed them.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter. I chose Switchboard because it is the junction in the home and the mains connection normally goes there. Nothing in the form said which was correct.
- **Connection dropdown:** My first attempt to set it didn't stick, because opening the price list closed it. I set it again later and confirmed it showed Switchboard before submitting.
- **Price pickers:** Both pickers listed both Amber sensors, and the Import price picker also accepts more than one. I picked each sensor by its name, not by its position in the list.

## add_grid_amber run 3: passed


I added the Grid to HAEO, and HAEO confirmed it with "Created configuration for Grid." A new Grid device with 12 entities now appears under Home.

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Limits:** import 55 kW, export 30 kW.

I didn't reopen the saved Grid to check the stored values. The form showed them correctly just before I submitted.

Points where I hesitated or made a mistake:
- **Connection choice:** The form defaulted to Inverter, and I wasn't told which part the grid attaches to. I chose Switchboard because it is the junction in the setup. If your grid actually connects through the inverter, this needs changing.
- **Wrong click:** I sent two clicks at once. The second one closed the import price list, so I reopened it. This had no effect on the result.
- **Price pickers:** The import and export price pickers allow several entries and offer both Amber sensors in each list. I picked only one in each, based on the sensor names.
- **Limit defaults:** The limit fields started at 100 kW. I replaced both values and confirmed the change in the form before submitting.

## add_load_constant run 1: passed


I added "Pool pump" to the Home hub as a Load. It now shows up as a new device with 12 entities. I set it to a fixed 0.8 kW and connected it to the Switchboard. I didn't open the new entry again to check the saved values.

Points where I hesitated or was unsure:
- **Connection:** The form defaulted to Inverter, and the only other option was Switchboard. I chose Switchboard because a pool pump is an ordinary household load. I couldn't confirm which one the existing "Load" uses, so this was a judgment call.
- **Fixed value:** The Forecast field looked like a list of sensors with no constant option. I typed 0.8 and it offered "Use 0.8 kW as a fixed value", which I picked. I only found that by trying it.
- **Shedding:** I left the Shedding section collapsed and unchanged. The pump runs all the time, so I didn't think it needed it.

## add_load_constant run 2: passed


"Pool pump" is now in HAEO as its own Load under the Home hub, with a fixed 0.8 kW power. HAEO showed "Created configuration for Pool pump", and the pump appears in the hub's device list.

Points where I hesitated:
- **Connection:** The form defaulted to Inverter, and the only other choice was Switchboard. I picked Switchboard because a pool pump is an ordinary household load. I didn't check which one your existing Load uses, so tell me if it should be on the Inverter instead.
- **Forecast field:** It looked like a sensor picker listing only solar and Sigen sensors. I typed 0.8 and it offered "Use 0.8 kW as a fixed value", which I chose. I wasn't sure at first that a constant was allowed.
- **Shedding:** I left that section collapsed and unchanged. The pump runs all the time, so I assumed the default was fine.

## add_load_constant run 3: passed


I added "Pool pump" as a Load in the Home hub, with a fixed power of 0.8 kW. It now shows up in the hub's device list. I didn't open its settings again afterwards, so I haven't re-read the saved 0.8 kW value.

Points where I hesitated or was unsure:
- **Connection:** The form defaulted to Inverter, but I chose Switchboard. A pool pump plugs into the house's AC wiring, so Switchboard seemed right. Nothing in the form said which one is correct, and I didn't check which one the existing "Load" uses.
- **Entering 0.8:** The Forecast field looked like a sensor picker, so it wasn't obvious how to enter a constant. Typing 0.8 made it offer "Use 0.8 kW as a fixed value", and I picked that.
- **Screen refresh:** After my first click on Load, the page looked unchanged. The dialog had only not rendered yet, so I looked again.
- **Shedding section:** I left it alone. A pump that runs all the time shouldn't need it.

## add_load_forecast run 1: passed


I added a Load named "Load" to the Home hub. It's connected to the Switchboard, and its Forecast field holds both Sigen sensors: Sigen Plant Consumed Power and Sigen Plant Consumed Power Forecast. HAEO showed "Created configuration for Load", and the Load now appears under Home. I didn't open it again to check the saved values.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter. I chose Switchboard because household consumption normally hangs off the switchboard. Nothing in the interface confirmed that was right.
- **Single "Forecast" field:** I expected separate fields for the forecast and the current reading. The form had one multi-select "Forecast" field, so I put both sensors in it. I'm not sure HAEO combines them the way I intended.
- **Dropdown mix-up:** My first attempt to change the Connection dropdown was interrupted when I opened the Forecast picker, so I had to redo it. The end result was correct.
- **Shedding section:** I didn't open or change it.

## add_load_forecast run 2: passed


I added a load named "Load" to your Home hub. It uses both Sigen sensors: Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power (the current reading). HAEO showed "Created configuration for Load", and the Load now appears under Home.

I didn't reopen the load to check how it saved the two sensors.

Points where I hesitated or went wrong:
- **Connection choice:** The form defaulted to Inverter. I changed it to Switchboard, because I took household consumption to sit on the main board. I couldn't confirm that from the interface, so please check it matches your wiring.
- **Both sensors in one field:** The only field for them was labelled "Forecast", and it accepted several sensors. I put the current-power sensor in there too. I assumed that is how HAEO wants a current reading, but nothing on screen said so.
- **Load name:** I kept the default name "Load".
- **Dropdown clicks:** My first click on the Connection dropdown didn't open it, so I clicked again. This had no effect on the result.

## add_load_forecast run 3: passed


I added a Load called "Household consumption" to your Home hub. It now appears in the hub's device list. It uses both Sigenergy sensors in its Forecast field:
- Sigen Plant Consumed Power Forecast (`sensor.sigen_plant_consumed_power_forecast`)
- Sigen Plant Consumed Power (`sensor.sigen_plant_consumed_power`)

I connected it to the Switchboard. I didn't open the Shedding section, so it's at its defaults.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter and offered only Inverter or Switchboard. I picked Switchboard because household consumption normally sits on the switchboard. I couldn't confirm that from the interface.
- **Name:** I chose "Household consumption" myself, since you didn't give one.
- **Current sensor in the Forecast field:** The form has no separate field for a current-power sensor. I added it to the same Forecast list, which accepted several entries. I don't know how HAEO combines the two sensors.
- **Submit:** My first Submit click only closed the dropdown, so I had to click it a second time. It didn't create anything twice.

## add_policy_battery_wear run 1: passed


I added a policy named "Battery wear" to your Home setup. It charges $0.01 per kWh whenever energy leaves the Battery, wherever that energy goes. I didn't run the optimizer to see the effect on its plan.

The policy has these settings:
- **Source:** Battery.
- **Target:** Any, which is the default. I left it alone so the cost applies to every destination.
- **Price:** a fixed value of 0.01 $/kWh. The price box first listed only the two Amber price sensors, so I typed 0.01 and picked the "fixed value" option.
- **Enabled:** on.

Home Assistant showed "Created configuration for Policies", and a new "Policies" device now appears under Home. I didn't open the policy again to check the saved values.

Points where I hesitated or was unsure:
- I assumed "Any" was already selected for Target, because no button looked highlighted in the page text. I didn't check this, and I didn't click it to confirm.
- I chose the name "Battery wear" myself, since you didn't give one.

## add_policy_battery_wear run 2: passed


I added a HAEO policy called "Battery wear". It charges $0.01 for every kWh the battery discharges, whatever the energy goes to. It's enabled and now shows under Policies on the integration page.

The policy has the source set to Battery, the target left on "Any", and a fixed price of 0.01 $/kWh.

I didn't open the saved policy again to read the values back. The only confirmation is the "Created configuration for Policies" message and the new Policies entry.

Points where I hesitated or was unsure:
- **Source and target buttons:** The Source and Target "Any / Elements" buttons gave no visible sign of which one was selected. I clicked "Elements" for Source and picked Battery, and the Battery chip appeared. I left Target alone, assuming "Any" was the default.
- **Price field:** The Price field first offered only the Amber price sensors. I typed 0.01 and chose the "Use 0.01 $/kWh as a fixed value" option, which turned it into a number field showing 0.01.
- **Policy name:** I picked "Battery wear" myself, since you didn't give one.

## add_policy_battery_wear run 3: passed


I added a Policy named "Battery wear" to the Home hub. It charges 0.01 $/kWh (1 cent) on energy leaving the Battery, whatever the destination. The source is the Battery, the target is Any, and the price is a fixed 0.01 $/kWh. Home Assistant showed "Created configuration for Policies", and a new Policies element now appears under the hub.

I didn't run the optimizer or look at its results, so I haven't seen the cost change a plan.

Points where I hesitated or was unsure:
- **Source list:** The source picker offered only Battery, Grid and Solar, not Load or Inverter. I assumed that was normal and picked Battery.
- **Price field:** It first listed only price sensors, so I wasn't sure a fixed number was allowed. Typing 0.01 produced a "Use 0.01 $/kWh as a fixed value" option, which I chose.
- **Target:** I didn't touch it because it already showed Any selected. That is the setting that covers every destination.
- **Name:** I chose "Battery wear" myself, since you didn't specify one.

## add_solar_forecast_solar run 1: passed


I added a Solar element to the Home hub and connected it to the Inverter. It uses all 32 Forecast.Solar estimated energy production sensors. That is east, north, south and west, each for today, tomorrow, the day after tomorrow, and days 3 to 7. HAEO confirmed "Created configuration for Solar", and Solar now shows up under Home. I didn't reopen the saved Solar settings to check them.

Points where I hesitated or made a mistake:
- **Connection:** The Connection field already said Inverter, so I left it. That matches "feeds into your inverter".
- **Sensor choice:** The picker also listed Solcast and Sigen PV sensors. I left those out because you asked for the Forecast.Solar ones only. The south sensors are named "South solar prediction forecast", but their IDs follow the same `energy_production_*_south` pattern, so I treated them as Forecast.Solar.
- **Selection count:** Each click selected one sensor and the list stayed open. I counted 32 remove buttons in the selected list, but I didn't check each one against the full set of sensors.
- **Blocked command:** My first attempt to click all the sensors in one shell loop was denied. I clicked them one at a time instead.

## add_solar_forecast_solar run 2: passed


I added a Solar element named "Solar" to HAEO, connected to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 days each (today, tomorrow, the day after, then 3 to 7 days out). HAEO showed "Created configuration for Solar." I counted 32 remove buttons in the selected list before submitting. After submitting I only checked that the Solar entry appeared on the page, not its saved settings.

Points where I hesitated or made a mistake:
- **Rejected loop:** I tried to click the options in a shell loop, and the environment refused it. I then clicked one at a time.
- **Failed first search:** My first filter search, "solar_east", matched nothing because it isn't part of the sensor names. "_east" worked.
- **Extra output:** I clicked a few options one by one before I noticed the "Add all N matches" shortcut. That made some output very long.
- **Connection:** The Connection field already said Inverter, so I left it. This matches what you described.
- **Other forecast sensors:** The list also had Solcast and Sigen sensors. I ignored them because you asked for Forecast.Solar only.
- **Curtailment:** I left the collapsed Curtailment section alone because you didn't mention it.

## add_solar_forecast_solar run 3: passed


I added a Solar element to HAEO, connected to the Inverter, with all 32 Forecast.Solar sensors selected. That is 8 sensors for each of east, north, south and west. For each direction: today, tomorrow, day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar." I didn't reopen Solar afterwards to check the saved list.

Points where I hesitated or hit problems:
- **Connection:** I left it on the default, Inverter, because you said the panels feed into the inverter. The only other choice was Switchboard.
- **Blocked command:** My first attempt to click the sensors in a shell loop was denied by the environment. I re-ran the clicks as chained commands instead.
- **Racy count check:** I ran two batches of clicks at the same time. The "Remove" button count I used to check them might have been unreliable. The full list I read back before submitting did show all 32.
- **Solcast sensors:** The picker also listed Solcast and Sigen sensors. I left them out because you asked for the Forecast.Solar ones only.
- **Names:** The south sensors are labelled "South solar prediction forecast", not "production". I counted them as Forecast.Solar because their entity IDs follow the same pattern as the other three directions.

## add_solar_solcast run 1: passed


I added a Solar element to your Home hub and connected it to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element again to check its saved settings.

I left the name as the prefilled "Solar" and didn't open the Curtailment section.

Points where I hesitated or slipped:
- **Forecast picker:** It let me select several sensors, and I wasn't sure at first that it would. I picked the first one, then searched "Solcast" and used "Add all 2 matches" for the other two.
- **Submit:** My first Submit click appeared to do nothing. The dialog stayed open, probably because it only closed the dropdown. A second click created the element.
- **Connection:** I left it on the prefilled "Inverter" without checking the other choice (Switchboard). That matches what you told me.

## add_solar_solcast run 2: passed


I added a Solar element to HAEO. It's connected to the Inverter and uses all three Solcast sensors as its forecast: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar." after I submitted. I didn't open the new Solar element again to check its saved settings.

Points where I hesitated or slipped:
- **Forecast picker:** It listed many similar sensors, including East, North, South and West production forecasts. I picked only the three Solcast PV Forecast sensors. I wasn't sure at first that the field accepted several sensors, so I added Today first and saw it was a multi-select.
- **Connection:** The dialog already showed Inverter, so I left it. That matches your setup, but I didn't open the dropdown to confirm it was a real selection rather than a default.
- **Curtailment:** I left that section collapsed and untouched, since you didn't mention it.

## add_solar_solcast run 3: passed


I added a Solar element to HAEO, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar." I didn't open the new element afterwards to re-check it.

Points where I hesitated or slipped:
- **First Submit click:** It seemed to do nothing, and the dialog stayed open. I think the click only closed the forecast dropdown. The second click went through.
- **Connection field:** It already showed Inverter, so I left it. I didn't change it myself.
- **Forecast field:** It wasn't obvious it accepted several sensors. I found out after picking the first one.
- **Similar sensors:** The list also held many "East/North/South/West solar production forecast" sensors. I left those out because only the Solcast ones matched what you asked for.
- **Curtailment:** I didn't open this section and left it at its defaults.

## edit_battery_min_charge run 1: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully". When I reopened the Battery settings, Min charge level read 20.

Hesitation points: none. One thing I assumed: I took the "Battery" button on the Battery row to be the one that opens its settings, and it did.

## edit_battery_min_charge run 2: passed


I raised the Battery's minimum charge level from 5% to 20%. I saved it and got "Configuration updated successfully". When I reopened the Battery settings, the field showed 20.

I left the reopened Battery settings dialog open instead of closing it. I didn't change anything else.

Points where I hesitated or made a mistake:
- **Where to click:** I wasn't sure which control opened the battery settings. I guessed the "Battery" button with the cog, and it was the right one.
- **Saved value:** After saving, the entity count went up by one (60 to 61). I didn't investigate why, and it may just be a new entity for the changed setting.

## edit_battery_min_charge run 3: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully". I reopened the Battery configuration afterwards, and it showed 20.

I changed only that one field and left the rest of the battery settings as they were.

Points where I hesitated or made a mistake: none.

# Benchmark runs

## add_battery run 1: passed


I added the Sigenergy battery to HAEO as "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery", but I didn't reopen the entry afterwards to check the saved values.

- **Capacity:** Sigen Plant Rated Energy Capacity sensor (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge sensor (12.8% at the time).
- **Max charge power:** Sigen Plant ESS Rated Charging Power sensor (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power sensor (19.2 kW).
- **Min charge level:** fixed at 5%, so it should never discharge below that.

I left the other fields at their defaults: max charge level, pricing, efficiency and advanced settings.

Points where I hesitated or slipped:
- The form's default connection was already Inverter, which matches your setup, so I kept it without checking anything else.
- I entered the 5% as a fixed value rather than a sensor, because you gave a plain number.
- The state of charge is only 12.8%, so the 5% floor is close to the current level. I didn't change anything because of that.
- I didn't make any mistakes that I noticed.

## add_battery run 2: passed


I added the battery to HAEO, and the form reported "Created configuration for Battery." I didn't reopen the battery afterwards to check the saved values.

- **Connection:** Inverter. This was the form's default and matches your setup.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8 %).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** 5 % as a fixed value, so it never discharges below that.

I left the pricing, max charge level, efficiency and advanced settings at their defaults.

Points where I hesitated or slipped:
- The charge power picker listed both rated power sensors with a "Select all" option. I picked only the charging one for that field, then searched again for the discharging one.
- For the 5% minimum, I typed "5" and chose the "Fixed value 5 %" option, because no sensor fit.
- I accepted the connection default (Inverter) without checking it against the other option, Switchboard.

## add_battery run 3: passed


I added the battery to HAEO as "Battery". HAEO showed "Created configuration for Battery", but I didn't reopen the entry afterwards to check the saved values.

- **Connection:** Inverter. I left the default, since you said the battery connects through your inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8% at the time).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** a fixed 5%, so the battery is never discharged below that.

I left the pricing, efficiency and advanced settings at their defaults.

Points where I hesitated or slipped:
- **Max charge power picker:** it offered "Select all 2" as well as the individual sensors. I chose the charging sensor directly so I wouldn't add both to one field.
- **Min charge level:** I wasn't sure at first whether a typed "5" would be taken as a number. The picker offered "Fixed value 5 %", so I chose that.

## add_grid_amber run 1: passed


I added the Grid to your Home hub. It now appears in the list of parts under the hub, and HAEO showed "Created configuration for Grid."

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter and offered only Inverter or Switchboard. I picked Switchboard because the grid supply normally comes in there. You didn't say which, so change it if your grid is wired to the inverter.
- **Connection dropdown:** My first click on it didn't select anything. When I came back to it, I chose Switchboard.
- **Default limits:** Both power limits started at 100 kW. I removed them and typed 55 and 30.
- **Not rechecked:** I confirmed the 55 kW and 30 kW values on the form before submitting. I didn't reopen the saved Grid to check them afterwards.

## add_grid_amber run 2: passed


I added the Grid to HAEO, and Home Assistant confirmed it with "Created configuration for Grid." I didn't reopen the Grid afterwards to check the saved values.

- **Connection:** Switchboard
- **Import price:** Amber Express - Home General Price
- **Export price:** Amber Express - Home Feed In Price
- **Import limit:** 55 kW
- **Export limit:** 30 kW

Points where I hesitated or slipped:
- **Connection choice:** The form offered only Inverter or Switchboard, and it defaulted to Inverter. I chose Switchboard because the grid usually enters the house there. You didn't say which one, so tell me if you want it on the Inverter instead.
- **Dropdown selections:** My first click on the Connection dropdown closed it without changing the value, so I set it again later. In the same step I picked the import price, which sits in a list that also contains the feed-in price. I checked that the right sensors were selected before submitting.
- **Default limits:** Both power limits started at 100 kW. I removed those values and typed 55 and 30. The first attempt at the export limit printed a very long page, so I checked the values by searching the page text.

## add_grid_amber run 3: passed


The Grid is now added to HAEO. HAEO showed "Created configuration for Grid." I didn't reopen the Grid afterwards to check the saved values.

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

Points where I hesitated or slipped:
- **Connection choice:** the form defaulted to Inverter. I chose Switchboard because the grid normally feeds the switchboard, but you didn't say which one, so that is my guess.
- **Dropdown didn't register:** my first click on the Connection dropdown only opened it, and it closed without a selection. I reopened it and picked Switchboard on the second try.
- **Default limits:** both power limits started at 100 kW. I removed those and typed 55 and 30.

## add_load_constant run 1: passed


"Pool pump" is now in HAEO as its own Load. It uses a fixed 0.8 kW and connects to the Switchboard. It shows up under the Home hub with 12 entities. I didn't open the new load afterwards to re-check its saved settings.

Where I hesitated or was unsure:
- **Connection:** The form defaulted to Inverter. I chose Switchboard because it is the junction that the home's loads would sit on. Nothing in the form said which was right, so this was a judgement call. I also didn't check which one the existing "Load" uses.
- **Fixed value:** The Forecast field is a search box, so I typed "0.8" and picked the "Fixed value 0.8 kW" option. I assumed that is how you enter a constant power.
- **Shedding:** I left the optional Shedding section collapsed and unchanged, since you said the pump runs all the time.
- **Connection dropdown:** I opened it twice, because the first time it didn't seem to take. The second time it did.

## add_load_constant run 2: passed


I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW forecast. After I submitted it, HAEO showed "Created configuration for Pool pump." The hub list now includes it, with 12 entities.

I connected it to the Switchboard and left "Allow shedding" off, which was the default. That means HAEO won't switch the pump off to save money, which matches a pump that runs all the time.

Points where I hesitated or made a mistake:
- **Connection choice:** The form defaulted to Inverter, with Switchboard as the only other option. I picked Switchboard because it seemed the right place for a household AC load. I couldn't confirm how the existing "Load" is connected, so this is a judgement call.
- **Parallel commands:** I ran two commands at once early on, and the connection dropdown and forecast field interfered with each other. I redid both steps one at a time. The saved result has the right values.
- **Unchecked sections:** I opened the Shedding section only to check its defaults. I didn't touch the optional "Consumption cost" field.

## add_load_constant run 3: passed


I added "Pool pump" to the Home hub as its own load. I set it to a fixed 0.8 kW and connected it to the Switchboard. HAEO showed "Created configuration for Pool pump", and the name now appears on the integration page. I didn't open the new load to check the saved values.

Points where I hesitated or made a mistake:
- **Connection choice:** The form offered only Inverter or Switchboard, and the Load form defaulted to Inverter. I chose Switchboard because a pool pump is a household load. I don't know where your existing Load is connected, so I couldn't match it.
- **Forecast field reset:** My first 0.8 kW entry was cleared when I changed the connection dropdown. I entered it again and picked "Fixed value 0.8 kW", which showed as a chip.
- **Stale reference:** I clicked an old reference once after the page had changed it. That click did nothing, and I redid it with the new one.
- **Screen refresh:** After my first click on "Load", the page looked unchanged until I waited a moment. The dialog was just slow to appear.

## add_load_forecast run 1: passed


I added a load called "Household consumption" to your Home hub. It now shows in the hub's list of parts.

- **Forecast sources:** I selected both `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power` in the load's Forecast field. That field accepted several sensors at once.
- **Connection:** I connected it to the Switchboard.
- **Not checked:** I only confirmed the load appears under Home, not that the forecast entries were saved as chosen.

Where I hesitated or was unsure:
- **Connection choice:** The form defaulted to Inverter. I chose Switchboard because household consumption normally hangs off the main switchboard. The form gave no guidance, so this is a judgement call.
- **Current power sensor:** I couldn't tell whether HAEO uses a current-power sensor alongside a forecast as intended. The form has only the one Forecast field, so I put both sensors in it.
- **Name:** I renamed the load from the default "Load" to "Household consumption". You didn't ask for that.
- **Closed dropdown:** The dropdown closed after my first selection. I reopened it and searched to add the second sensor.
- **Skipped section:** I left the optional "Shedding" section untouched.

## add_load_forecast run 2: passed


I added a Load called "Household consumption" to your Home hub. HAEO showed "Created configuration for Household consumption", and the load now appears as a device with 12 entities. I didn't open the load again to check its saved settings.

- **Connection:** Switchboard.
- **Forecast field:** I selected both `sensor.sigen_plant_consumed_power_forecast` (the forecast) and `sensor.sigen_plant_consumed_power` (the current consumed power). The field accepts several sensors, and both are in it.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter. I chose Switchboard because household consumption normally sits on the switchboard, but nothing on the page said which was right.
- **Current sensor:** The form has no separate field for it. I put it in the same Forecast field as the forecast sensor. I'm not sure how HAEO combines the two sensors.
- **Name:** The form pre-filled "Load". I renamed it "Household consumption", which was my own choice.
- **Mistake:** I clicked the Connection dropdown before the Forecast field. That did nothing harmful, but it was an unnecessary step.

## add_load_forecast run 3: passed


I added a Load called "Household consumption" to the Home hub. It appears in the hub's device list, so it saved. I didn't open it again to check the saved settings.

- **Connection:** I connected it to the Switchboard, since household consumption is a whole-house load.
- **Sensors:** The Forecast field accepted more than one sensor. I selected both `sensor.sigen_plant_consumed_power_forecast` (the forecast) and `sensor.sigen_plant_consumed_power` (the current consumed power).
- **Name:** I chose "Household consumption" myself, replacing the default "Load".

Points where I hesitated or was unsure:
- **Where the current sensor goes:** The form has no separate field for it. I assumed the multi-select Forecast field was the right place. I couldn't confirm that HAEO combines the two sensors the way I intended.
- **Connection choice:** The form offered only Inverter and Switchboard. I picked Switchboard without any guidance from the form.
- **Shedding:** I didn't open or change the Shedding section.

## add_policy_battery_wear run 1: passed


I added a policy named "Battery wear" to the Home hub. It charges $0.01/kWh for any energy leaving the Battery, whichever element receives it. It saved with a "Created configuration for Policies" message, and a new Policies device now appears under the hub.

The settings are:
- **Source:** Battery.
- **Target:** Any.
- **Price:** a fixed value of 0.01 $/kWh.
- **Enabled:** yes.

I only checked that the policy saved. I didn't run an optimisation to confirm it changes the plan.

Points where I hesitated or wasn't sure:
- **Price sign and direction:** I assumed a positive price on a Battery-to-Any policy means a cost on discharge. The form didn't say so, and I didn't check the policy afterwards.
- **Target "Any":** I left it on Any to cover "wherever that energy goes". I couldn't tell whether that also counts energy moving from the Battery to the Battery itself.
- **Policy name:** I chose "Battery wear" myself, since you didn't give one.
- **Price entry:** typing 0.01 only worked after I clicked the "Fixed value 0.01 $/kWh" option the field offered.
- **Delay:** I was slow to give you a status update partway through.

## add_policy_battery_wear run 2: passed


I added a policy named "Battery wear" to the Home hub. It has source set to Battery, target left on Any, and price 0.01 $/kWh. That should charge 1 cent for every kWh the battery discharges, wherever the energy goes. HAEO showed a success message. A new "Policies" device with 2 entities now appears under Home.

I didn't run an optimisation afterwards, so I haven't seen the cost show up in a plan.

Where I hesitated or slipped:
- **Policy element:** HAEO has no obvious "battery wear" option. I chose Policy because its description is about controlling power flows between elements.
- **Target:** I never clicked the Target "Any" button. I assumed it was already selected and didn't confirm it before submitting.
- **Price units:** I assumed the price field means dollars per kWh. The option I picked was labelled "0.01 $/kWh", so that looks right.
- **Final check:** I didn't reopen the policy to check the saved values. I relied on the success message and the new device.

## add_policy_battery_wear run 3: passed


I added a policy called "Battery wear" that charges 0.01 $/kWh (1 cent) for energy discharged from the Battery, whatever it goes to. I reopened it afterwards: the source is Battery and the price is 0.01 $/kWh. The policy is enabled.

I didn't run the optimizer, so I haven't seen the cost show up in a plan.

- **Hesitation:** I wasn't sure whether to use the Policy button or the Battery element's own settings. I chose Policy because the Add policy form has a price per kWh and a source/target choice.
- **Target:** I left Target on "Any" without clicking it, because it looked like the default. I couldn't see which option was highlighted. After saving, no target elements were listed, so it should mean any destination.
- **Name:** The new device shows up as "Policies", not "Battery wear". The policy inside it has the name I gave it.

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO, connected to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, each with today, tomorrow, and days 2 to 7.

HAEO showed "Created configuration for Solar." I didn't reopen the Solar entry afterwards to check the saved list. Before I submitted, the field showed the selected sensors.

I picked the sensors by searching for `sensor.energy_production`, which gave exactly 32 matches, and using "Select all". I left the Solar entry's name at its default, "Solar". I didn't touch the Curtailment section.

Points where I hesitated or could have gone wrong:
- **Search filter:** I trusted it to match only the Forecast.Solar sensors. The Solcast and Sigen sensors dropped out of the list, and the 32 left matched 4 directions × 8 days.
- **Connection:** I accepted the default of Inverter without comparing it to Switchboard. It fits your description of the panels feeding the inverter.

## add_solar_forecast_solar run 2: passed


I added a Solar element to the "Home" hub and connected it to the Inverter. It uses all 32 Forecast.Solar sensors. That is 8 for each of the four directions: today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears on the integration page. I didn't open the new element afterwards to check its saved settings.

I typed `energy_production_` into the forecast picker to filter the list. "Select all" then offered exactly 32 sensors, so I used it. I left out the Solcast and Sigen sensors.

Points where I hesitated or slipped:
- **Connection:** I kept the default, Inverter, without checking the alternative (Switchboard). You said the panels feed the inverter, so I took that as right.
- **South sensor names:** the South sensors are labelled "solar prediction forecast" instead of "production forecast". I treated them as Forecast.Solar sensors because their entity IDs follow the same `energy_production_*_south` pattern.
- **Curtailment:** I didn't open this section and left it at its defaults.
- **Select all:** I used it without scrolling through the filtered list again to confirm every item. I did check that the 32 selected items covered each direction and day.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub, connected to the Inverter, with all 32 Forecast.Solar sensors as its forecast. Home Assistant showed "Created configuration for Solar."

- **Sensors:** The 32 are eight per direction (east, north, south, west): today, tomorrow, the day after tomorrow, and 3 to 7 days from now. Before submitting, the field showed 32 selected entries.
- **Left out:** Solcast and Sigen sensors were also in the list, and I didn't select them.
- **Not re-checked:** I didn't reopen the saved Solar element to confirm the sensors had stuck.
- **Left alone:** I didn't touch the Curtailment section.

Points where I hesitated or was unsure:
- **Connection:** The Connection field already defaulted to Inverter, which matches your setup, so I left it. It also offered Switchboard.
- **South sensors:** The South sensors are named "solar prediction forecast" rather than "production forecast". I included them because their entity IDs follow the same `energy_production_*_south` pattern.
- **Selection method:** I typed `energy_production_` into the search to narrow the list to exactly those sensors, then used "Select all". I'm assuming it only selected the filtered 32 rather than all 41, and the count of 32 removable entries supports that.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub and connected it to the Inverter. For its forecast I picked the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. Solar now appears in the hub list with 1 device and 4 entities, and the entity count went from 56 to 60. I didn't open the new entities or check their values.

I left the default name "Solar", and I left the optional Curtailment section closed and unchanged.

Points where I hesitated or made a mistake:
- **Forecast picker:** It closed after each pick. The first time, I didn't expect that, so I had to search "solcast" again for each of the other two sensors.
- **Similar-looking sensors:** The list also held many `energy_production_*` sensors (East, North, South and West arrays) and Sigen plant sensors. I ignored them, since you asked for Solcast.

## add_solar_solcast run 2: passed


I added a Solar element to HAEO and connected it to the Inverter. It uses all three Solcast forecast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO said "Created configuration for Solar", and Solar now appears in the Home hub's list of parts.

I left the name as the default "Solar" and didn't open the Curtailment section.

Points where I hesitated or slipped:
- **Forecast picker:** It closed after each pick, so I had to reopen it and search "solcast" twice to add the other two sensors. I confirmed all three were selected before submitting.
- **Wrong-looking sensors:** The list also held many similar-looking sensors (East, North, South and West production forecasts, plus Sigen Plant sensors). I ignored them because you asked for Solcast.
- **Connection:** It was already set to Inverter, so I left it. I didn't check whether Switchboard might also be a sensible choice, since you said the panels feed the inverter.

## add_solar_solcast run 3: passed


I added a Solar element to the Home hub, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears in the hub with 1 device and 4 entities.

I didn't open the Curtailment section, so those settings are untouched.

Points where I hesitated or made a mistake:
- **Forecast picker:** It listed many similar "solar production forecast" sensors for the East, North, South and West arrays. I picked only the three whose names start with "Solcast PV Forecast".
- **Connection:** I left it on its default, Inverter, without opening the dropdown to check the other choice (Switchboard). It matched your description of the panels feeding the inverter.
- **Re-typing the search:** The picker cleared my search text after each selection, so I typed "solcast" again before picking each sensor. This was a minor inefficiency, not an error.

## edit_battery_min_charge run 1: passed


The battery's minimum charge level is now 20% instead of 5%. HAEO showed "Configuration updated successfully" after I submitted, and when I reopened the Battery settings the field read 20 %.

I left the reopened Battery settings dialog open rather than closing it, since I'd already reported the task as done.

Points where I hesitated or slipped:
- **Entering the value:** the Min charge level field offers entities as well as typed values. I typed 20 and chose the "Fixed value 20 %" option from the list rather than assuming typing alone would register.
- **Opening the settings:** I wasn't sure which button opened the battery settings, so I took the "Battery" button on the Battery row. That turned out to be the right one.

## edit_battery_min_charge run 2: passed


I raised the battery's minimum charge level from 5% to 20%. After I submitted the form, HAEO showed "Configuration updated successfully". I didn't reopen the battery's settings afterwards to check the saved value.

To change it, I opened the Battery configuration from the Home hub. In the Limits section I removed the fixed 5% value and typed 20. I picked the "Fixed value 20 %" option and then submitted.

Points where I hesitated:
- **Removing the old value:** Removing the 5% chip opened a dropdown that only offered the battery state-of-charge sensor. I wasn't sure typing a number would work from there, but it did.
- **Dropdown option:** After typing 20, I had to click the "Fixed value 20 %" option for it to register as the value.
- **Battery state of charge:** The sensor shows 12.8%, which is below the new 20% minimum. I didn't change anything about that.

## edit_battery_min_charge run 3: passed


I raised the Battery's minimum charge level from 5% to 20%, and Home Assistant showed "Configuration updated successfully". I didn't reopen the Battery settings afterwards to confirm the new value, so that message is the only confirmation.

Removing the 5% value made the field offer the battery's state-of-charge sensor as a suggestion. I typed 20 instead and chose the "Fixed value 20 %" option, so the minimum is a fixed number and not tied to a sensor.

The battery's charge is currently 12.8%, which is below the new 20% minimum. I didn't change anything about that.

Points where I hesitated or made a mistake: none. I did not pause on any step.

# Benchmark runs

## add_battery run 1: passed


I added the battery to HAEO as "Battery", and HAEO confirmed with "Created configuration for Battery." I didn't reopen the entry afterwards to check the saved values. I did check the form before submitting, and every sensor showed as selected.

- **Connection:** Inverter (DC), which was the default. I kept it because your battery connects through the inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8% at the time).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** a fixed 5%, so it should never discharge below that.

I left the pricing fields (salvage value, charge cost, discharge cost) at their defaults. I also left max charge level, battery efficiency and the advanced settings untouched, since you didn't mention them.

Points where I hesitated or slipped:
- The Connection field offered Inverter (DC) or Switchboard (AC). I assumed DC from "connected through your inverter", without checking it against the entry afterwards.
- The first time I typed into the discharging-power search box, I only checked that the right option appeared. I confirmed it was selected when I reviewed the form just before submitting.
- After typing "5" in Min charge level, I had to pick the "Fixed value 5 %" option from the dropdown. Typing alone doesn't set it.
- I didn't look at the battery's device page afterwards to see its new entities.

## add_battery run 2: passed


I added a battery named "Battery" to the Home hub, and Home Assistant showed "Created configuration for Battery." I didn't reopen the new battery afterwards to check the saved values. I did check the form before submitting, in a screenshot and in the page text.

- **Connection:** Inverter. This was the default, and you said the battery connects through your inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8% when I picked it).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** a fixed 5%, so it should never discharge below that.

I left the max charge level, pricing, efficiency and advanced settings at their defaults.

Points where I hesitated or was unsure:
- I picked the Inverter connection without checking what the other option (Switchboard) would change. I chose it only because the form's default matched your description.
- The power sensors weren't easy to find in the long entity list. I typed "rated charging" and "rated discharging" to filter it, then picked the exact Sigen entities.
- I typed "5" into the min charge level box, which offered it as a fixed 5% value. I assumed that is the right way to enter a constant.

## add_battery run 3: passed


I added the Sigenergy battery to HAEO as "Battery". HAEO showed "Created configuration for Battery", but I didn't reopen the entry to check the saved values.

- **Connection:** Inverter (DC). I left the default because the battery is connected through your inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8% at the time).
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).
- **Min charge level:** a fixed 5%, so it should never discharge below that.

I left the pricing fields, the max charge level and the efficiency and advanced sections at their defaults.

Points where I hesitated or slipped:
- When I searched "charging" in the max charge power field, the picker offered a "Select all" option and listed both the charging and discharging sensors. I picked only the charging one.
- I wasn't sure whether typing "5" would be stored as a percentage. The picker offered "Fixed value 5 %", so I chose that.

## add_grid_amber run 1: passed


I added the Grid to your Home hub in HAEO. HAEO showed "Created configuration for Grid", and Grid now appears in the Home hub's device list.

- **Connection:** Switchboard (AC). It was already selected by default and fits a grid connection, so I left it.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I did not reopen the Grid entry after saving to check the stored values. I only saw the limits and prices in the form before I submitted it.

Points where I hesitated or slipped:
- **Switchboard:** I was briefly unsure whether to keep it as the connection, since I didn't know which part the grid should attach to. I kept it because it was preselected.
- **Power limits:** The section was collapsed, and both limits defaulted to 100 kW. I had to remove those defaults and enter 55 and 30 as fixed values.
- **Typing into the price field:** My first `amber` search in the import price field was unnecessary, because the list already showed both Amber sensors. It didn't cause any problem.

## add_grid_amber run 2: passed


I've added the grid connection to HAEO, and it now shows in the Home hub's list.

- **Connection:** Switchboard. This was already selected, and I left it because the grid supplies the AC side of the house.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I only confirmed the Success message and the Grid entry in the list. I didn't reopen the Grid entry to check the saved values.

Points where I hesitated or was unsure:
- **Switchboard connection:** I wasn't sure it was right. I kept the default without checking it against my wiring.
- **Price pickers:** Both pickers listed the same two Amber sensors, so I chose by name. I assumed "General Price" is the buy price and "Feed In Price" is the sell price.
- **Limit defaults:** Both limits started at 100 kW. I removed those and typed the new values. I checked each value as it was entered but not after saving.

## add_grid_amber run 3: passed


The Grid is now part of your Home hub, and HAEO confirmed it with "Created configuration for Grid." After I closed the dialog, the Grid showed up in the hub's device list. I didn't reopen it to check the saved values.

- **Connection:** Switchboard (AC). It was already selected, and a grid connection belongs on the AC side with the inverter and load.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

Points where I hesitated or slipped:
- **Power limits:** The section was collapsed, and both limits defaulted to 100 kW. I had to remove each default before typing the new value. After typing 55, I pressed Enter and checked that it showed as a fixed value. I did the same for 30.
- **Connection choice:** I didn't ask whether Switchboard was the right connection. I accepted the default because the Inverter option was labelled DC, with Battery and Solar.
- **Wasted step:** When I removed the 100 kW import default, the dropdown opened with 41 unrelated sensors, such as solar forecasts. I ignored them and typed the number.

## add_load_constant run 1: passed


I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW power value. It now appears in the hub's device list.

It's connected to the Switchboard (AC). I didn't change the Shedding section.

Where I hesitated:
- **Connection:** The form offered Inverter (DC) or Switchboard (AC). I kept the default, Switchboard, because a pool pump is a normal household AC load. I didn't check how your home is wired.
- **Fixed value:** The forecast field asks for a sensor or a value. I typed 0.8 and picked the "Fixed value 0.8 kW" option, since you said the pump draws about 0.8 kW all the time.

## add_load_constant run 2: passed


I added "Pool pump" to HAEO as a new load under Home. It uses a fixed value of 0.8 kW and connects to the Switchboard. HAEO showed "Created configuration for Pool pump", and the name now appears in the Home hub's list.

Points where I hesitated or made assumptions:
- **Connection:** I left it on Switchboard (AC), which was already selected. I assumed a pool pump plugs into the house's AC supply. I didn't check this against your wiring.
- **Forecast field:** It asked for a forecast, not a plain power number. Typing 0.8 offered a "Fixed value 0.8 kW" option, which I picked as the way to enter a constant.
- **Shedding:** I didn't open this section and left it at its defaults.

## add_load_constant run 3: passed


I added "Pool pump" to the Home hub as a Load with a fixed power of 0.8 kW. It now shows in the hub's device list with 12 entities, and HAEO confirmed "Created configuration for Pool pump."

I left the connection on Switchboard (AC), which was already selected, since a pool pump runs off the house's AC supply. I didn't open Shedding, so I don't know what it does.

Points where I hesitated:
- **Connection:** I wasn't certain Switchboard was right, because the form didn't say which option suits a household appliance. I judged it from the AC/DC labels.
- **Forecast field:** It asked for a "forecast", so I wasn't sure a plain number was allowed. Typing 0.8 offered a "Fixed value 0.8 kW" option, and I picked that.
- **Check:** I only checked the device list on the integration page, not the entity values.

## add_load_forecast run 1: passed


I added a Load named "Load" to your Home hub, connected to the Switchboard. HAEO showed "Created configuration for Load", and the hub now lists 7 devices (it had 6).

Both Sigen sensors went into the Load's Forecast field:
- `sensor.sigen_plant_consumed_power_forecast`
- `sensor.sigen_plant_consumed_power`, the current consumed power

I didn't reopen the Load to check how it saved the two sensors.

Points where I hesitated:
- **One field for both sensors:** The form has no separate field for current consumed power. I wasn't sure the Forecast field was the right place for it, but it accepts several sensors, so I put both there.
- **Connection:** I left it on the default, Switchboard. That seemed right for whole-house consumption, but I didn't check it against your wiring.
- **Name and Shedding:** I kept the default name "Load" and didn't open the Shedding section.

## add_load_forecast run 2: passed


I added a load called "Household" to HAEO and connected it to the Switchboard. Its Forecast field holds both Sigen sensors: Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power. HAEO showed "Created configuration for Household", and Household now appears in the Home hub's device list. I didn't check that HAEO actually uses the two sensors.

Points where I hesitated or was unsure:
- **Current sensor:** The form had one multi-select "Forecast" field and no separate field for current power. I put both sensors in it. I'm not certain HAEO treats the current-power sensor the way you intended.
- **Connection:** I left the default, Switchboard (AC), because household consumption sits on the AC side. The form didn't say which option was right.
- **Name:** I changed the default "Load" to "Household". The name was my choice.
- **Sensor selection:** My first attempt to pick the current sensor, a search that only filtered the output, didn't select it. I added it with a second attempt and confirmed both sensors appeared as selected before submitting.

## add_load_forecast run 3: passed


I added a Load called "Household" to the Home hub. It uses both Sigenergy sensors: Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power (the current reading). The success dialog said "Created configuration for Household", and the hub now lists Household with 12 entities.

Points where I hesitated or made a judgement call:
- **Connection:** I left it on Switchboard (AC), which was already selected. I assumed that's right for whole-home consumption, but I didn't check how your Switchboard is wired.
- **Name:** I changed the default "Load" to "Household". The name was my choice, since you didn't give one.
- **Current sensor in the Forecast field:** The form had no separate field for the current consumed power sensor. The Forecast picker accepts several entities, so I added both there. I'm not certain HAEO treats a non-forecast sensor correctly in that field. I didn't open the Load afterwards to check how it was stored.
- **Shedding:** I didn't open the optional Shedding section and left it at its defaults.

## add_policy_battery_wear run 1: passed


I added a policy called "Battery wear" to the Home hub. It charges $0.01/kWh (a fixed price) for energy coming from the Battery, going to any destination. A new "Policies" device now shows on the integration page with 2 entities, so the save took effect. I haven't run the optimizer to see the cost applied.

Points where I hesitated or was unsure:
- **Choosing "Policy":** I picked it because it was the only element type that looked like it could put a price on energy leaving the battery. The Battery element's own settings might have a discharge-cost field instead. I didn't open them to check.
- **Target setting:** I assumed the Target control already defaulted to "Any" and left it alone. The interface didn't clearly show which option was selected. Source "Elements" and Target "Any" were my reading of the buttons.
- **Price entry:** Typing 0.01 offered a "Fixed value 0.01 $/kWh" choice, which I picked. I assumed the unit was dollars per kWh because the option said so.

## add_policy_battery_wear run 2: passed


I added a policy named "Battery wear" to the Home hub. It charges 1 cent ($0.01) for every kWh that leaves the battery. HAEO showed "Created configuration for Policies", and a new "Policies" device now appears under Home. I did not open the policy again to check the saved values.

The policy is enabled, with these settings:
- **Source:** the Battery element.
- **Target:** Any, so the cost applies wherever the discharged energy goes.
- **Price:** a fixed value of 0.01 $/kWh.

Points where I was unsure:
- **Policy as the route:** I assumed a Policy was the right element for this. Nothing else in the "Add" list looked closer, and the form's description matched ("control how power flows between elements").
- **Target "Any":** I left it on Any without testing it. I assumed it also covers energy going back into the battery's own inverter or other elements.
- **Name:** The name "Battery wear" was my own choice, since you didn't give one.

## add_policy_battery_wear run 3: passed


I added a policy called "Battery wear" in HAEO. It charges $0.01 for every kWh the Battery discharges, whatever the energy goes to. Source is Battery, Target is Any, the price is a fixed 0.01 $/kWh, and the policy is enabled. I reopened it from the Policies list and the saved values matched.

Points where I hesitated:
- **Choosing a Policy:** I picked "Policy" over "Buffer" or editing the Battery itself, because it was the only element with a source, a target and a price. I couldn't confirm that from any help text.
- **Price unit:** the price field showed "0.01 $/kWh" as a fixed-value option, so I took that as the unit.
- **Target setting:** the Any/Elements toggle doesn't show which option is selected. I concluded Target was "Any" because the saved policy listed no target elements. The Source toggle reordered itself on reopening, which made it harder to read.
- **Closing the edit dialog:** I closed it with the X after checking, without submitting. The policy was unchanged.

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO and connected it to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, each with today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar," and Solar now appears in the Home hub's device list. I didn't open the new Solar entry to check its saved settings.

I left the name as "Solar" and the connection on "Inverter, DC", the default. That fits panels that feed into your inverter.

I picked the sensors by typing `energy_production_` in the forecast picker. That narrowed the list to exactly 32 and I used "Select all". It left out the Solcast and Sigen sensors, which are a different forecast source.

Points where I hesitated or was unsure:
- The Forecast.Solar sensors are named differently by direction ("East solar production forecast", "South solar prediction forecast"). I relied on the shared `sensor.energy_production_…` entity IDs to be sure I had all four directions.
- I assumed "Inverter, DC" was the right connection rather than "Switchboard, AC". I didn't change it because you said the panels feed into the inverter.
- I left the optional Curtailment section untouched.

## add_solar_forecast_solar run 2: passed


I added a Solar element to HAEO and connected it to the Inverter (DC). It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 days for each direction. HAEO showed "Created configuration for Solar." After I clicked Finish, a Solar entry appeared on the integration page. I didn't open it again to check the saved settings.

I found the sensors by typing `sensor.energy_production` into the Forecast picker. That filtered the list to exactly 32, and I used "Select all". The 8 days per direction are today, tomorrow, the day after tomorrow, and 3 to 7 days from now.

Points where I hesitated or was unsure:
- **Connection:** The default was already Inverter (DC). I kept it because you said the panels feed the inverter.
- **Sensor list:** I assumed the 32 filtered `energy_production` sensors were all Forecast.Solar ones. Their names carried the direction and "Estimated energy production".
- **Names:** The south sensors are labelled "solar prediction forecast" rather than "solar production forecast". I included them as the south set.
- **Other forecasts:** I left out the Solcast and Sigen sensors, since you asked for Forecast.Solar only.
- **Curtailment:** I didn't open that section, so it's at its default.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub. It connects to the Inverter and uses all 32 Forecast.Solar sensors: east, north, south and west, each with eight days (today, tomorrow, day after tomorrow, and 3 to 7 days from now). HAEO showed "Created configuration for Solar", and Solar now appears in the hub's list of elements. I didn't open the new element again to check the saved settings.

Points where I hesitated or was unsure:
- **Connection:** The dialog already had "Inverter, DC" selected. I kept it because your panels feed the inverter.
- **Picking sensors:** I typed "energy_production_" to filter the list. That left exactly the 32 Forecast.Solar sensors, so I used "Select all". I left out the Solcast and Sigen sensors.
- **Sensor names:** The south sensors are labelled "solar prediction" instead of "solar production". I included them because their entity IDs match the other directions.
- **Curtailment:** I didn't open or change that section.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub and connected it to the Inverter. I picked all three Solcast sensors as its forecast: Forecast Today, Forecast Tomorrow and Forecast Day 3. After I submitted, HAEO showed "Created configuration for Solar". A Solar device with 4 entities now appears on the integration page. I didn't open the new device to check its entity values.

Points where I hesitated or slipped:
- **Forecast field:** It accepts several sensors at once, but the list closed after each pick. I had to search "solcast" and open it again for each of the three sensors.
- **Connection:** The Connection setting already had "Inverter" selected, which matched your setup. I left it as it was.
- **Other sensors in the list:** The list also offered many similar solar forecast sensors (East, North, South and West). I ignored them because you asked for Solcast.

## add_solar_solcast run 2: passed


I've added the Solar element in HAEO and finished the task. It's connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears in the Home hub's device list. I didn't open the new entry again to check the saved values.

Points where I hesitated or slipped:
- **Connection:** "Inverter" was already selected. I left it because your panels feed the inverter, and the option was labelled DC.
- **Forecast picker:** The picker allows several selections, and it closed after each pick. I reopened it twice by searching "solcast". I checked that all three sensors showed as chosen before submitting.
- **Other sensors:** The list also held many similarly named sensors, such as East, North, South and West production forecasts. I ignored those and used only the ones named "Solcast PV Forecast".
- **Curtailment:** I didn't touch the Curtailment section. You didn't mention it.

## add_solar_solcast run 3: passed


I added a Solar element to the Home hub, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears as a device with 4 entities. I didn't open the Solar entry again to check the saved settings.

Points where I hesitated or was unsure:
- **Connection:** The form had Inverter pre-selected. I kept it because you said the panels feed into your inverter.
- **Forecast picker:** It accepts several sensors and closes after each pick. I had to reopen it and search to add the second and third sensors.
- **Other forecast sensors:** The list also had East, North, South and West solar forecasts that aren't Solcast. I ignored them.
- **Curtailment:** I left that section alone.
- **Wrap-up:** I ended the task before posting this summary, so I'm giving it now.

## edit_battery_min_charge run 1: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully." When I reopened the Battery settings, they showed 20%. The task is finished and I've recorded it as done.

Points where I hesitated or made a mistake: none. One thing was unclear at first. Removing the 5% value opened a list of entity suggestions instead of a number box. Typing 20 offered a "Fixed value 20 %" option, which I picked.

## edit_battery_min_charge run 2: passed


I raised the Battery's minimum charge level from 5% to 20%. After saving, Home Assistant showed "Configuration updated successfully". I reopened the Battery settings and the field now reads 20 %.

Points where I hesitated or slipped:
- **Opening the settings:** I wasn't sure which control opened the Battery settings. I guessed the "Battery" button in the Battery row, and it was right.
- **Entering the value:** I first removed the 5 % value, then typed 20 into the empty field. Pressing Enter turned it into a fixed value of 20 %. Before that, the field offered the state-of-charge sensor as a suggestion. I ignored it and kept a fixed number.

## edit_battery_min_charge run 3: passed


I raised the battery's minimum charge level from 5% to 20%, but I couldn't reopen the Battery settings afterwards to confirm it. Home Assistant showed "Configuration updated successfully" after I submitted.

I opened the Battery configuration, removed the fixed 5% value and entered 20. The field showed "Fixed value 20 %" before I submitted. My re-check was blocked: Bash permission was denied for that last command. I didn't try to work around the block, and I didn't call `./browse done`.

Where I hesitated or was unsure:
- **Unverified save:** The success message is the only evidence the change took effect.
- **Editing the value:** The 5% value had no edit box, so I had to remove it and add 20 as a new fixed value. I wasn't sure that would work until the field showed 20 %.
- **Sensor suggestion:** After I removed the 5%, the field offered the battery state-of-charge sensor as a suggestion. I ignored it and kept a fixed value.

# Benchmark runs

## add_battery run 1: passed


I added the Sigenergy battery to HAEO as "Battery", connected to the Inverter. HAEO showed a "Created configuration for Battery" success message. I didn't reopen the entry afterwards to check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor.
- **State of charge:** the Sigen Plant Battery State of Charge sensor.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor.
- **Min charge level:** 5%, typed in as a fixed number.

I left every other setting at its default, including the pricing fields.

Points where I hesitated or slipped:
- **Entity pickers:** the first click on several "Choose entities" buttons didn't open the picker. I clicked again each time, and the picker opened on the second click.
- **Submit:** the first click on Submit only closed the open dropdown. The second click submitted the form.
- **Connection:** I kept the default "Inverter" and didn't compare it with "Switchboard". You said the battery connects through the inverter, so I assumed the default was right.

## add_battery run 2: passed


I added the battery to HAEO as "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery", and Battery now appears on the integration page. I didn't open the new battery entry to check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor, currently 32.24 kWh.
- **State of charge:** the Sigen Plant Battery State of Charge sensor, currently 12.8%.
- **Minimum charge level:** 5%, so the battery is never discharged below that.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor, currently 16.8 kW.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor, currently 19.2 kW.

I left the name, the pricing fields, and the efficiency and advanced settings at their defaults. I also left "Max charge level" empty, since you didn't give a ceiling.

Points where I hesitated or made a mistake:
- I wasn't sure whether to rename the battery or choose the Switchboard connection instead. I kept the default name and picked Inverter because you said the battery connects through your inverter.
- Some entity picker clicks didn't open the list on the first try, and the first click on the Max discharge power picker did nothing. I clicked again and they worked.
- Searching for "rated charging" showed both the charging and discharging power sensors. I picked the charging one for Max charge power and searched again for the discharging one.
- I didn't check the hub's total device or entity counts after submitting.

## add_battery run 3: passed


I added the Sigenergy battery to HAEO as "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery", but I didn't reopen the entry afterwards to check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor, which read 32.24 kWh.
- **State of charge:** the Sigen Plant Battery State of Charge sensor, which read 12.8%.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor, which read 16.8 kW.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor, which read 19.2 kW.
- **Minimum charge level:** 5%, typed in as a fixed number.

I left everything else at its default, including the pricing fields and the Max charge level.

Points where I hesitated or slipped:
- **Connection:** I kept the default "Inverter" without checking the alternative, "Switchboard". You said the battery is connected through your inverter, so I believe it's right.
- **Picker confirmation:** after choosing a sensor, the picker stayed open, so I wasn't sure the choice had registered. I pressed Escape and saw the sensor listed under the field.
- **Max charge power search:** the list for this field showed 41 entities, mostly solar forecasts. I picked the right one by its name and entity ID.

## add_grid_amber run 1: passed


I added the Grid to HAEO, and Home Assistant confirmed with "Created configuration for Grid." I didn't reopen the entry afterwards to check the saved values.

- **Connection:** Switchboard
- **Import price:** Amber Express - Home General Price
- **Export price:** Amber Express - Home Feed In Price
- **Import limit:** 55 kW
- **Export limit:** 30 kW

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter, and I wasn't told which part the grid attaches to. I picked Switchboard because a grid supply normally enters the house there. If your grid actually connects through the inverter, that needs changing.
- **Dropdown misclick:** My first click on the Connection dropdown closed it without selecting anything. I reopened it and chose Switchboard on the second try.
- **Price pickers:** Both price pickers listed the same two Amber sensors, so I checked the names. I chose General Price for import and Feed In Price for export.
- **Power limits:** The import and export limits were prefilled with 100 kW. I replaced them with 55 and 30.

## add_grid_amber run 2: passed


I added the Grid to HAEO. It now shows up under the Home hub, and the setup dialog reported "Created configuration for Grid."

- **Connection:** I connected it to the Switchboard.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Limits:** 55 kW import and 30 kW export, replacing the default 100 kW for each.

I didn't reopen the Grid afterwards to check the saved values.

Points where I hesitated or made a mistake:
- **Connection choice:** The form defaulted to Inverter, and I wasn't told which part the grid attaches to. I chose Switchboard because a grid supply normally enters the home there. If your grid actually connects through the inverter, that choice is wrong.
- **Dropdown mistake:** My first click on the Connection dropdown only opened it, and I then moved on to the price fields. I came back and picked Switchboard afterwards, and the form showed it selected.
- **Price pickers:** After I picked an entity, each picker stayed open, so I pressed Escape to close it before moving on.
- **Power limits:** That section was collapsed at first, and I had to expand it to find the fields.

## add_grid_amber run 3: passed


I added the Grid to HAEO, and HAEO showed "Created configuration for Grid."

- **Connection:** Switchboard
- **Import price:** Amber Express - Home General Price
- **Export price:** Amber Express - Home Feed In Price
- **Import limit:** 55 kW
- **Export limit:** 30 kW

I didn't reopen the Grid afterwards to check the saved values. I did see the 55 and 30 in the form before I submitted it.

Points where I hesitated or made a mistake:
- **Connection:** It defaulted to Inverter. I chose Switchboard because it's the junction and a grid normally connects there, but nothing told me which was right.
- **First attempt at the connection:** My first attempt to open the Connection dropdown didn't change the value, so I set it again at the end. It then showed Switchboard.
- **Power limits:** They were collapsed and defaulted to 100 for both. I opened the section and typed the values in.

## add_load_constant run 1: passed


I added "Pool pump" as its own load in the Home hub, with a constant 0.8 kW forecast. It's connected to the Switchboard. HAEO showed "Created configuration for Pool pump", and the new entry now appears in the hub's list.

Where I hesitated:
- **Connection:** The form offered only Inverter or Switchboard, and it defaulted to Inverter. I picked Switchboard because a pool pump is a household load. I didn't check which one the existing Load uses, so that choice is a guess.
- **Shedding:** I left the Shedding section collapsed and unchanged, since the pump runs all the time.

## add_load_constant run 2: passed


"Pool pump" is now in HAEO as its own load, set to a constant 0.8 kW and connected to the Switchboard. HAEO showed "Created configuration for Pool pump", and the new load appears under the Home hub. I didn't open it afterwards to re-check the 0.8 kW value.

Points where I hesitated:
- **Connection:** The form defaulted to Inverter, but I chose Switchboard. I assumed a pool pump is an ordinary household load on the switchboard, not something on the inverter. I couldn't tell how the existing Load is connected, so this is a guess. If your pump is wired differently, change it under Configure.
- **Constant power:** The Forecast field takes either a number or a sensor. I typed 0.8 as a fixed kW value because you said the pump runs all the time at about that draw.
- **Shedding:** I left the Shedding section collapsed and unchanged, since you didn't mention it.

## add_load_constant run 3: passed


I added "Pool pump" as its own Load in the Home hub, with a constant 0.8 kW and connected to the Switchboard. It now shows up in the hub list as a Load with 12 entities. I didn't open the new load afterwards to check the saved values.

Points where I hesitated:
- **Connection choice:** the form offered only Inverter or Switchboard, and it defaulted to Inverter. I chose Switchboard because a pool pump is an ordinary household load on the AC side. Nothing in the form said which was right, so this is my judgement.
- **Forecast field:** it is labelled "Forecast" but accepts a plain number in kW. I entered 0.8 there because the pump runs all the time at a steady draw. I'm assuming that field is how HAEO takes a constant value.
- **Shedding:** I left this section collapsed and unchanged, since you didn't mention it.

## add_load_forecast run 1: passed


I added a Load called "Household" to your Home hub. It now shows up in the list of parts.

- **Connection:** Switchboard. I assumed household consumption belongs there, not on the Inverter.
- **Forecast sensors:** Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power. The Forecast field accepted both, so I added both.

I haven't checked that HAEO combines the two sensors the way you intend.

Points where I hesitated or slipped:
- **Connection choice:** The form defaulted to Inverter. I wasn't sure which was right, so I picked Switchboard.
- **Dropdown click:** I opened the connection dropdown, then clicked the entity picker without choosing anything. I went back and set Switchboard before submitting.
- **Name:** I changed the default name "Load" to "Household". You didn't give a name.
- **Final check:** I confirmed "Household" appears in the list, but I didn't reopen it to check the saved settings.

## add_load_forecast run 2: passed


I added a Load called "Household" to Home. HAEO confirmed "Created configuration for Household", and the load now appears under Home. I didn't open it again afterwards to check the saved values.

- **Forecast:** I selected both Sigen sensors in the one Forecast field: "Sigen Plant Consumed Power Forecast" and the current "Sigen Plant Consumed Power". The field accepts several sensors, so I added both there.
- **Connection:** I set it to Switchboard.

Points where I hesitated or slipped:
- **Connection choice:** The dropdown offered only Inverter (the default) and Switchboard. I chose Switchboard because household consumption normally sits on the switchboard, but nothing in the form said which was right.
- **Forecast field:** HAEO has no separate field for the current consumed power sensor. I wasn't sure whether putting both sensors in the Forecast field would combine them sensibly, and I didn't confirm how HAEO uses them together.
- **Dialog still open:** Pressing Escape after picking the sensors didn't close the dialog, so I carried on with the form, which was fine.
- **Late updates:** I went quiet for a while during the steps and should have said what I was doing.

## add_load_forecast run 3: passed


I added a Load called "Household" to HAEO. It uses both Sigen sensors: Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power, the current reading. HAEO showed "Created configuration for Household", but I didn't reopen the load afterwards to check its saved settings.

Points where I hesitated or was unsure:
- **Connection:** The choices were Inverter and Switchboard. I picked Switchboard because household consumption normally sits on the switchboard, but the form didn't say which was right.
- **Where the sensors go:** There is only one multi-select "Forecast" field, so I put the current-power sensor in it next to the forecast sensor. I don't know how HAEO combines a live sensor with a forecast sensor.
- **Name:** I chose "Household" myself, since you didn't give a name.
- **Skipped:** I left the "Shedding" section unopened.

## add_policy_battery_wear run 1: passed


I added a Policy named "Battery wear" to Home. It has Battery as the source, Target set to Any, and a price of 0.01 $/kWh. The policy is enabled. I didn't run the optimizer to see the cost take effect. After I submitted, the integration page showed a new "Policies" entry with 2 entities, so HAEO accepted the policy.

Hesitations:
- **Policy as the right element:** There's no obvious "battery wear" setting. I chose Policy over editing the Battery because it can price power flowing from one element to another.
- **Sign of the price:** I assumed a positive price is a cost on the discharged energy rather than a credit. The form didn't say.
- **Target "Any":** I left Target on Any to cover wherever the energy goes. From the screenshot, Any looked selected by default, but I didn't confirm it after submitting.
- **Not reopened:** I didn't reopen the saved policy to check its values.

## add_policy_battery_wear run 2: passed


I added a policy called "Battery wear" that charges $0.01 for every kWh the battery discharges, whatever the destination. I didn't open the policy again or look at the Policies entities, so I haven't confirmed how HAEO applies it. HAEO showed "Created configuration for Policies", and a new Policies element now appears under Home.

The policy is enabled, with the source set to Battery, the target set to Any, and the price set to 0.01 $/kWh.

Points where I hesitated or was unsure:
- **Target setting:** I assumed "Any" was already selected, because the screenshot showed it highlighted. I never clicked it myself.
- **Price direction:** The form only said "Price". I assumed a positive price means a cost on that flow, not a reward. I couldn't check this from the interface.
- **Self-flows:** I'm not sure whether "Any" as the target also covers battery-to-battery flows. I assumed it doesn't matter for wear.
- **Typing errors:** My first attempt to type into the price field returned the page without showing the value. The later screenshot showed 0.01, so I treated it as fine.

## add_policy_battery_wear run 3: passed


I added a policy called "Battery wear" with Battery as the source, Target left on "Any", and a price of 0.01 $/kWh. That should charge 1 cent for every kWh the battery discharges, wherever it goes. HAEO confirmed "Created configuration for Policies", and a new "Policies" device now appears under Home.

I didn't reopen the policy to check the saved values, and I haven't seen the optimiser's output change.

Points where I hesitated or was unsure:
- **Target setting:** I didn't click either Target button. I assumed "Any" was the default because the form gave no sign of which was selected. The Source list did look selected after I picked Battery.
- **Battery-to-battery flow:** "Any" may include energy that goes back into the battery itself. I assumed that was fine, since you asked for the cost to apply wherever the energy goes.
- **Source list:** After I clicked "Elements" for Source, the picker showed only an empty list item. I had to click it before the Battery, Grid and Solar options appeared.
- **Price direction:** The Price field didn't say whether a positive value is a cost or a payment. I assumed positive means a cost.

## add_solar_forecast_solar run 1: passed


I added Solar to the HAEO hub "Home" and connected it to the Inverter. It uses all 32 Forecast.Solar sensors. That is east, north, south and west, each with today, tomorrow, the day after tomorrow and days 3–7. HAEO showed a "Created configuration for Solar" confirmation, and Solar now appears on the hub with 4 entities.

I searched "sensor.energy_production_" first, and the list narrowed to exactly those 32. I then used "Select all", so no Solcast or Sigen sensors were included.

I didn't check the solar sensors' values or the optimizer output afterwards. I also left the Curtailment section alone.

Points where I hesitated or slipped:
- The Connection field was already set to Inverter. I kept it because you said the panels feed the inverter, not the Switchboard.
- The Forecast field showed a "kW" number box next to the entity picker. I ignored it and used the entity picker, because I was told to use the sensors.
- The sensors measure energy in kWh, not power. I didn't know whether HAEO converts them, so I can't say whether that matters.
- I didn't open the Curtailment section, so I don't know what its defaults are.
- I made no mistakes that I'm aware of.

## add_solar_forecast_solar run 2: passed


I added a Solar element to the "Home" hub and connected it to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors for each direction. Each direction has today, tomorrow, the day after tomorrow, and 3 to 7 days from now.

HAEO showed "Created configuration for Solar", and the hub page now lists a Solar device with 4 entities. I didn't open the Solar element again to check its saved settings.

Points where I hesitated or made a mistake:
- **Connection:** the form already had "Inverter" selected, which matches your setup, so I left it.
- **Picking the sensors:** the picker's "Select all" would have added all 41 entities, including Solcast and Sigen sensors. I typed `energy_production` first, which narrowed it to exactly the 32 Forecast.Solar sensors, and then used "Select all".
- **Forecast number box:** the form also has a kW number box for the forecast. I left it empty and used the sensor picker.
- **Blocked command:** one of my commands, a Submit click piped through a filter, was denied by the environment. I reran it without the filter and it worked.

## add_solar_forecast_solar run 3: passed


I added a Solar element to HAEO and connected it to the Inverter. It uses all 32 Forecast.Solar energy production sensors: east, north, south and west, with 8 sensors per direction. The 8 per direction are today, tomorrow, the day after tomorrow, and 3 to 7 days from now. I counted 32 entries in the Forecast list before submitting. HAEO then showed "Created configuration for Solar", and Solar now appears in the Home hub's element list.

Points where I hesitated or was unsure:
- **Sigen and Solcast sensors:** the entity picker also listed Sigen Plant and Solcast sensors, which aren't Forecast.Solar. "Select all" at first covered 41 entities, so I typed `energy_production` into the picker's search box first. That narrowed it to exactly the 32 Forecast.Solar sensors, and I then used "Select all".
- **Connection:** I left the Connection field at its default of Inverter, since the panels feed the inverter. Switchboard was the only other choice.
- **Unchecked options:** I didn't open the Curtailment section, and I didn't check how HAEO combines the 32 sensors into one forecast.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears under the Home hub on the integration page. I didn't open it again to check the saved settings.

Points where I hesitated or slipped:
- **Forecast field:** it also had a fixed kW number box, but I left that empty and used only the sensors. I assumed the sensors were enough, and the form accepted it.
- **Curtailment:** I left the optional Curtailment section untouched.
- **Duplicate-looking sensors:** the picker listed other solar forecast sensors (East, North, South, West). I ignored them because you asked for Solcast.
- **Output dump:** one command printed far more page text than I needed. It didn't change anything.

## add_solar_solcast run 2: passed


I added a Solar element to the Home hub, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. Home Assistant showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element afterwards to check its saved settings.

Points where I hesitated or slipped:
- **Connection:** the form already had Inverter selected, and I left it, since that matches your setup.
- **Forecast picker:** after I clicked the first Solcast sensor I wasn't sure it had registered. The picker stays open after each pick, so I re-read the page and confirmed all three were listed.
- **Escape key:** I pressed Escape before submitting, to close the picker. It didn't close the whole dialog, but I wasn't sure it would.
- **Other fields:** I left the Curtailment section alone, and I didn't set any value in the forecast number box.

## add_solar_solcast run 3: passed


I added a Solar element to the Home hub, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. Solar now shows on the integration page with 1 device and 4 entities, and the hub total went from 6 devices to 7. I didn't open the new entities to check their values.

Points where I hesitated or could have gone wrong:
- **Name:** I kept the default name "Solar" rather than choosing my own.
- **Connection:** the Connection dropdown already showed Inverter, so I left it. It also offered Switchboard, but the panels feed the inverter.
- **Picker list:** the entity picker listed 41 sensors, including four other solar forecast sets (East, North, South, West) and the Sigen PV power sensor. I picked only the three Solcast ones, since those are the ones you named.
- **Selection feedback:** the picker stayed open after each click, so I couldn't tell at first whether a click had registered. I confirmed each one from the checkmarks and the list above the picker.
- **Optional sections:** I didn't open the Curtailment section, and I left the "kW" number box next to the Forecast field empty. Picking sensors was enough for the form to submit.
- **Units:** the Solcast sensors report energy in kWh while the field says kW. I assumed HAEO handles that conversion and didn't check.

## edit_battery_min_charge run 1: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully". When I reopened the Battery configuration, Min charge level read 20.

I changed nothing else in the battery settings.

Points where I hesitated or made mistakes: none. I opened the Battery configuration through the "Battery" button on the integration page, which was my best guess. It was the right one.

## edit_battery_min_charge run 2: passed


I raised the Battery's minimum charge level from 5% to 20%. Home Assistant showed "Configuration updated successfully". When I reopened the Battery configuration, Min charge level read 20.

I didn't hesitate or make any mistakes. One thing to know: the battery's current state of charge showed 12.8%, which is below the new 20% minimum. I didn't check how HAEO handles that.

## edit_battery_min_charge run 3: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO said "Configuration updated successfully". When I reopened the Battery configuration, Min charge level showed 20.

I didn't hesitate and didn't make any mistakes. I left the other battery settings as they were.

# Benchmark runs

## add_battery run 1: passed


I added the battery to HAEO as "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery", but I didn't reopen the entry afterwards to check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor.
- **State of charge:** the Sigen Plant Battery State of Charge sensor.
- **Minimum charge level:** a constant 5%, so it should never discharge below that.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor.

I left everything else at its default, including the pricing values, the efficiency settings and the advanced options. I also left the max charge level unset.

Points where I hesitated or slipped:
- **Connection:** I kept "Inverter" as the connection. It was the default and you said the battery is connected through your inverter, but I didn't check that Switchboard was the wrong choice.
- **Power sensor lists:** the power pickers listed many unrelated sensors, such as solar forecasts. I chose the two ESS rated power sensors by name. After picking them I only searched the page text for the sensor names, which didn't confirm each one landed in the right field.
- **Sensor confirmation:** I never checked the Capacity and State of charge fields again after choosing them. The only confirmation was the success message.

## add_battery run 2: passed


I added the Sigenergy battery to HAEO as "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery", and a Battery entry now appears under Home. I didn't reopen the entry to check the saved values.

- **Capacity:** the "Sigen Plant Rated Energy Capacity" sensor.
- **State of charge:** the "Sigen Plant Battery State of Charge" sensor.
- **Max charge power:** the "Sigen Plant ESS Rated Charging Power" sensor.
- **Max discharge power:** the "Sigen Plant ESS Rated Discharging Power" sensor.
- **Minimum charge level:** 5% as a constant, so it should never discharge below that.

I left every other setting at its default, including max charge level (None), pricing and efficiency.

Points where I hesitated or slipped:
- The Connection field defaulted to Inverter, and I kept it. The choice was Inverter or Switchboard. You said the battery is connected through your inverter, so Inverter seemed right.
- The Capacity field looked like it was already in Entity mode, so I clicked the Entity button anyway. It didn't seem to change anything.
- The discharge power search matched both the charging and discharging sensors. I picked the discharging one from the list.
- One command in my first discharge-power search was denied by the environment. I reran it in a simpler form.

## add_battery run 3: passed


I added the battery to HAEO under the name "Battery", connected to the Inverter. HAEO showed "Created configuration for Battery" after I submitted. I didn't reopen the battery afterwards to check the saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor.
- **State of charge:** the Sigen Plant Battery State of Charge sensor.
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor.
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor.
- **Min charge level:** a constant 5%, so it is never discharged below that.

I left the other fields (max charge level, pricing, efficiency, advanced) at their defaults.

Points where I hesitated or was unsure:
- I kept the default name "Battery" because you didn't give one.
- I chose "Inverter" as the connection rather than "Switchboard", since you said the battery connects through the inverter.
- The power-limit pickers listed many unrelated sensors, so I searched for "rated charging" and "rated discharging" to find the right ones.
- I used the screenshot to confirm the min charge level and power sensors before submitting. I didn't confirm the capacity and state of charge fields the same way.

## add_grid_amber run 1: passed


The Grid is now added to your "Home" hub, and it shows up in the hub's device list with 12 entities. I didn't open it again to check the saved values. I only saw the "Created configuration for Grid" confirmation.

- **Connection:** Switchboard
- **Import price:** Amber Express - Home General Price
- **Export price:** Amber Express - Home Feed In Price
- **Import limit:** 55 kW
- **Export limit:** 30 kW

Points where I hesitated or slipped:
- **Connection choice:** I wasn't sure whether the grid should connect to the Inverter or the Switchboard. The form defaulted to Inverter. I chose Switchboard because a grid connection normally comes in at the switchboard, but nothing in HAEO told me which was right.
- **Connection dropdown:** My first click on the Connection dropdown didn't select anything. I clicked the Import price field while it was open, which closed it. I then reopened it and picked Switchboard.
- **Silent form behaviour:** The power limits started at 100 kW each. I changed both to your figures. I also typed both numbers in one step, so I confirmed each field showed its new value before submitting.

## add_grid_amber run 2: passed


I added the Grid to your Home hub. HAEO showed "Created configuration for Grid", and the Grid now appears in the hub's list with 12 entities.

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I didn't reopen the Grid to re-read the saved values.

Points where I hesitated or made a mistake:
- **Connection choice:** The form offered only Inverter or Switchboard, with Inverter preselected. You didn't say which to use. I chose Switchboard because a grid connection normally comes in at the switchboard. If your grid actually connects through the inverter, change this.
- **Connection dropdown:** My first attempt to open it closed without selecting anything, so I set it again at the end. It showed Switchboard before I submitted.
- **Power limits:** Both limits started at 100 kW, so I overwrote them with 55 and 30. The fields showed 55 and 30 before I submitted.
- **Price pickers:** They list entities in a different order from what I expected. I checked the names after picking each one.

## add_grid_amber run 3: passed


The Grid is now in your Home setup. HAEO showed "Created configuration for Grid", and a Grid device with 12 entities appeared in the hub.

- **Connection:** Switchboard.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I didn't reopen the Grid to re-read its saved values. I only saw the form fields as I filled them and the success message.

Points where I hesitated or slipped:
- **Connection choice:** I wasn't told whether the grid should attach to the Inverter or the Switchboard. I chose the Switchboard, assuming it is the point where the grid meets the house, but that is a guess.
- **Dropdown didn't register the first time:** My first click on the Connection dropdown closed without changing anything, and the field still read "Inverter". I reopened it and selected Switchboard, and it then showed Switchboard.
- **Power limits:** They were collapsed and defaulted to 100 kW each. I expanded the section and typed 55 and 30.

## add_load_constant run 1: passed


I added "Pool pump" to the Home hub as a Load with a constant power of 0.8 kW. It now shows up in the hub's list of parts, with 12 entities.

Points where I hesitated or was unsure:
- **Connection:** The form offered only Inverter or Switchboard, and it defaulted to Inverter. I chose Switchboard because a pool pump is an ordinary household load. I couldn't see what the existing "Load" is connected to, so I couldn't check that against it.
- **Forecast type:** The form defaulted to picking an entity. I switched it to "Constant", since you gave a fixed 0.8 kW and no sensor.
- **Shedding:** I left this section collapsed and unchanged. I didn't check what its defaults are.

## add_load_constant run 2: passed


"Pool pump" is now in HAEO as a Load with a constant 0.8 kW. It shows up in the Home hub with its own device and 12 entities.

I didn't open the new entry again to check the saved values. The only confirmation is the "Created configuration for Pool pump" message and the new device in the hub.

Points where I hesitated or was unsure:
- **Connection:** The form offered only Inverter or Switchboard, and it defaulted to Inverter. I chose Switchboard because a pool pump is an ordinary household load. I didn't check which one your existing "Load" uses, so that was a judgement call.
- **Constant power:** I took "runs all the time at about 0.8 kW" to mean the Constant option set to 0.8. I didn't use the Entity option.
- **Shedding:** I left the Shedding section collapsed and at its defaults, since you didn't mention it.
- **Narration:** I went quiet for a few steps near the end and had to be prompted for an update.

## add_load_constant run 3: passed


I added "Pool pump" to the Home hub as a Load with a constant power of 0.8 kW. It now shows in the hub list with 12 entities, and the device count went from 7 to 8. I didn't open the new load to check its saved values.

Where I hesitated or was unsure:
- **Connection:** The form offered only Inverter or Switchboard, and I didn't know which was right. I chose Switchboard because it seemed the natural place for a household load. I didn't check what the existing "Load" connects to. If your pump hangs off the inverter, that's worth changing.
- **Forecast type:** The form defaults to an entity picker, so I switched it to Constant to enter 0.8 kW.
- **Shedding:** I didn't open the Shedding section and left it at its defaults. I assumed it isn't needed for a pump that runs all the time.

## add_load_forecast run 1: passed


I added a Load called "Load" to the Home hub. Its forecast uses both Sensor entities, "Sigen Plant Consumed Power Forecast" and "Sigen Plant Consumed Power". The Home hub now lists the Load as a new device with 12 entities. I didn't open the Load afterwards to check the saved settings.

Points where I hesitated:
- **Connection:** I wasn't sure whether the load belongs on the Inverter or the Switchboard. I picked the Switchboard because household consumption is normally drawn from there. The form defaulted to Inverter, so change this if your wiring differs.
- **Current sensor:** There was no separate field for the current consumed power sensor. I added it as a second entity in the same Forecast list and assumed that is how HAEO wants it.
- **Name:** I kept the default name "Load" rather than choosing a more descriptive one.
- **Shedding:** I did not open or change the Shedding section.

## add_load_forecast run 2: passed


I added a Load named "Load" to HAEO, connected to the Switchboard. Its Forecast field has two entities: Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power. HAEO showed "Created configuration for Load". The Load device now appears with 12 entities, and the hub total went from 6 to 7 devices.

I didn't open the new Load to check how it uses the two sensors.

Points where I hesitated or guessed:
- **Connection:** The form offered only Inverter or Switchboard, and the default was Inverter. I chose Switchboard because household consumption normally sits there. That was a guess, and I had no way to confirm it.
- **Where the current sensor goes:** There was no separate field for the current consumed power sensor. I added it as a second entity in the same Forecast list, after seeing the picker accept several entities. I'm not sure that's how HAEO intends the current reading to be used.
- **Name:** I left the default "Load" rather than naming it something like "Household".

## add_load_forecast run 3: passed


I added a Load named "Household" to HAEO, and HAEO confirmed it was created. I only checked that "Household" now shows in the hub's list, and I didn't open it again to check the saved settings. It uses both Sigen sensors: "Sigen Plant Consumed Power Forecast" and "Sigen Plant Consumed Power". I put them together in the load's single Forecast field, since the form has no separate field for a current-power sensor. I left the Shedding section at its defaults.

Points where I hesitated or made a mistake:
- **Connection choice:** The form offered only Inverter or Switchboard, and I chose Switchboard. I assumed household consumption hangs off the switchboard, but I'm not certain that matches your wiring.
- **Wrong sensor picked:** When adding the second sensor, I clicked the wrong entry and selected "Sigen Plant ESS Rated Charging Power". I removed it and added "Sigen Plant Consumed Power" before submitting.
- **Combined sensors:** I'm not sure HAEO combines a forecast sensor and a live power sensor in that one field the way you intended. It was the only place the form accepted both.
- **Load name:** I chose "Household" myself, replacing the default "Load".

## add_policy_battery_wear run 1: passed


I added a policy called "Battery wear" that charges $0.01 for every kWh discharged from your Battery, whatever the energy goes to. HAEO confirmed it was created, and a new "Policies" device now shows on the integration page. I didn't run an optimisation to see its effect on the plan.

The policy is enabled. Its source is Battery, its target is Any, and its price is a constant 0.01 $/kWh.

Points where I hesitated or was unsure:
- **Direction of the price:** I assumed the price applies to energy flowing out of the source. I couldn't confirm that from the form, which only says it controls how power flows between elements.
- **Source choices:** The source picker offered only Battery, Grid and Solar. It didn't offer Load, Inverter or Switchboard. I picked Battery as intended.
- **Target setting:** I never clicked the Target "Any" button. It was already selected, which I confirmed on a screenshot.
- **Delay:** I went a while without telling you what I was doing after the "Success" dialog appeared.

## add_policy_battery_wear run 2: passed


I added a policy named "Battery wear" to Home. It charges 0.01 $/kWh (1 cent) for every kWh the Battery discharges, whatever the destination. Home Assistant reported success, and a new "Policies" device with 2 entities now appears under Home.

The policy is enabled, with the source set to Battery, the target set to Any and a constant price. I didn't open the saved policy again to check its values. I also didn't see HAEO's optimiser results change.

Points where I hesitated or was unsure:
- **Direction of the price:** I assumed a positive price in a policy is a cost on the energy flow. The form didn't say so, and I didn't confirm it.
- **Source and target choice:** I chose source = Battery with target = Any, so the cost applies wherever the discharged energy goes. The Target "Any" setting looked selected in the screenshot, but the page tree didn't show it.
- **Entry creation:** I was never asked which hub the policy belonged to. It created a separate "Policies" element, which I take to be the normal behaviour.

## add_policy_battery_wear run 3: passed


I added a policy called "Battery wear" to the Home hub. It charges $0.01 for every kWh that leaves the Battery, wherever that energy goes. The settings are:

- **Source:** Battery
- **Target:** Any
- **Price:** 0.01 $/kWh
- **State:** enabled

HAEO confirmed the save. I reopened the policy and saw the same values, but I haven't run an optimization to see the cost applied.

Points where I hesitated or was unsure:
- **Target setting:** I never clicked it, and I couldn't tell from the form which of Any or Elements was selected by default. I assumed Any. On reopening, the Target showed no elements listed, which fits Any, but the form doesn't mark the selection clearly.
- **Feature choice:** I wasn't certain a Policy was the right feature for a per-kWh discharge cost. It was the only option that matched, so I used it.
- **Policy name:** I chose "Battery wear" myself, since you didn't give one.

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO, connected to the Inverter, with all 32 Forecast.Solar estimated energy production sensors. That is East, North, South and West, with 8 sensors each (today, tomorrow, day after tomorrow, and 3 to 7 days from now). The form accepted it and showed "Created configuration for Solar." I did not open the new Solar entry afterwards to check how it saved.

Points where I hesitated or went wrong:
- **Name:** I kept the default name "Solar" and left the Curtailment section alone, since you didn't mention either.
- **Connection:** I left it at Inverter because you said the panels feed into your inverter.
- **South sensor names:** The South sensors are called "South solar prediction forecast…" while the others are "…solar production forecast…". I assumed they belong to Forecast.Solar and added them, because the other three directions had no South counterpart.
- **Slow adding:** The picker adds one sensor at a time, so it took 32 rounds. I tried to automate it with a shell loop, which was denied, so I did it by hand.
- **Mistyped search:** I typed into the wrong search box once and the command errored harmlessly.
- **Guessed refs:** I predicted element refs for several clicks without looking first. A couple landed on a different day than I expected, but I confirmed in the final list that every sensor appeared exactly once.

## add_solar_forecast_solar run 2: passed


I added a Solar element to the Home hub, connected to the Inverter. It uses all 32 Forecast.Solar sensors: East, North, South and West, with 8 days of forecast each. Home Assistant showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the saved Solar element to check the 32 sensors again. I did count 32 sensors in the form just before I submitted it.

Points where I hesitated or made a mistake:
- **Sensor names:** The South sensors are named "South solar prediction forecast…", while the others say "solar production forecast". I included them because they are clearly the South direction's Forecast.Solar sensors.
- **Picking the sensors:** The picker took one sensor at a time, so I had to add 32 separately. I used keyboard selection (ArrowDown, then Enter) to speed this up.
- **Typing in the search box:** My first attempt failed because I used the wrong ref. A click I made while the picker was still opening also seemed not to register, so I re-checked the list and redid it.
- **Skipped sensors:** I skipped the Solcast and Sigen sensors because they aren't Forecast.Solar.
- **Connection and Curtailment:** I left Connection on its default, Inverter, because the panels feed the inverter. I didn't open the Curtailment section.
- **Blocked shell commands:** Two shell commands (a loop helper and an awk filter) were blocked. I did those steps by hand instead.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors: East, North, South and West, each for 8 days (today through 7 days from now). HAEO showed "Created configuration for Solar." I confirmed the final list of 32 in the form before I submitted it. I didn't open the saved element afterwards to check it again.

Points where I hesitated or made mistakes:
- **Wrong sensors added by mistake:** My keyboard shortcut for picking entities also added 9 unrelated sensors (Sigen Plant and Solcast ones) to the list. I removed them one by one and checked the list before submitting.
- **Failed searches added more strays:** When I narrowed the picker by typing "South", the search box reference changed each time, so a few typed searches missed. That added 3 more Sigen sensors, which I also removed.
- **South sensors named differently:** The South sensors are called "solar prediction forecast" while the others say "production forecast". I checked that all 8 were Forecast.Solar sensors and included them.
- **Connection not changed:** I left the Connection at its default, Inverter, because the solar feeds into the inverter. I didn't touch the Curtailment section.
- **Blocked commands:** Several of my shell commands were denied, so I went step by step, which cost extra actions.

## add_solar_solcast run 1: passed


I added a Solar element to your Home hub and connected it to the Inverter. Its forecast uses the three Solcast PV Forecast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears in the hub with 4 entities.

I left the Curtailment section alone and did not open it.

Points where I hesitated or made a mistake:
- **Wrong sensor added:** On the third pick I added "South solar prediction forecast – 3 days from now" instead of Day 3. The sensor list had reordered after each pick, so the reference I used pointed at a different row. I noticed in the next screenshot, removed it, reopened the list and picked "Solcast PV Forecast Forecast Day 3". The final list was correct before I submitted.
- **Unclear multi-select:** I wasn't sure at first whether the Forecast field accepted more than one sensor. It showed an "Add entity" button, so I added Today, Tomorrow and Day 3 as separate entries.
- **Similar sensors:** The list also held East, North and South solar forecast sensors. I ignored them because you said Solcast.
- **Connection default:** The Connection field already said "Inverter", so I left it as it was.
- **Final check:** My check was the hub page showing Solar with 4 entities. I did not open the saved configuration to read the forecast list back.

## add_solar_solcast run 2: passed


I've added Solar to HAEO and connected it to the Inverter. Its forecast uses the three Solcast PV Forecast sensors: Today, Tomorrow and Day 3. HAEO showed "Created configuration for Solar", and Solar now appears on the integration page. I didn't open the saved Solar entry again to re-check its settings.

Points where I hesitated or made a mistake:
- **Wrong sensor picked:** I picked a "South solar prediction forecast" sensor by mistake when adding the third forecast entity. The picker list had shifted after each addition, so my saved reference pointed at a different row. I removed it, reopened the picker, and chose "Solcast PV Forecast Forecast Day 3" instead.
- **Search box didn't work:** Typing "Solcast" into the picker's search box timed out, so I scrolled the list and clicked entries instead.
- **Connection assumed:** The Connection field already said Inverter, so I left it. You said the panels feed the inverter, so I think that's right.
- **Curtailment skipped:** I didn't open the optional Curtailment section, since you didn't mention it.
- **Other sensors ignored:** The picker also listed East, North and South solar forecast sensors. I ignored them because you asked for Solcast.

## add_solar_solcast run 3: passed


Solar is now in HAEO, connected to the Inverter. Its forecast uses the three Solcast sensors: Today, Tomorrow and Day 3. Home Assistant said "Configuration updated successfully" after my fix. I didn't reopen the Solar settings afterwards to check the saved list.

The Solar entry now shows 1 device and 4 entities. I left the Curtailment section alone.

Points where I hesitated or made a mistake:
- **Wrong sensor saved first:** I picked the wrong third forecast sensor. The picker list had shifted after each pick, and I clicked "South solar prediction … 3 days from now" instead of "Solcast PV Forecast Forecast Day 3". I submitted before noticing. I then reopened Solar, removed that entry, added the Day 3 sensor and saved again.
- **Several forecast sensors:** The forecast field takes several sensors through "Add entity". I assumed Solcast's three sensors are meant to be added together, because the field allows more than one.
- **Look-alike sensors:** The picker also listed East, North and South solar sensors that look like forecasts. I took "Solcast PV Forecast" to be the Solcast one you meant, since you named it.

## edit_battery_min_charge run 1: passed


I raised the battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully". When I reopened the Battery settings, the field showed 20.

I changed only that one field and left the other battery settings as they were.

Points where I hesitated or made a mistake: none.

## edit_battery_min_charge run 2: passed


I raised the Battery's minimum charge level from 5% to 20%. I opened the Battery's configuration, changed "Min charge level" to 20 and submitted. HAEO showed "Configuration updated successfully". I didn't reopen the configuration afterwards to confirm the 20% was saved. The only evidence is that success message.

Points where I hesitated or made a mistake:
- I wasn't sure which button opened the Battery's settings. I guessed the "Battery" button (not the "Edit device" one) and it opened "Battery configuration".

## edit_battery_min_charge run 3: passed


I raised the Battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully" after I submitted. When I reopened the Battery configuration, Min charge level read 20.

I left the reopened dialog open without a second submit, so nothing else was changed.

Points where I hesitated or slipped:
- The Battery was listed twice on the page, once as a config entry and once as a device. I clicked the entry's "Battery" configure button and it opened the right dialog.
- The entity count went from 60 to 61 after saving, which I didn't expect from a single value change. I didn't investigate it, and the new entity may just be something HAEO created on reload.

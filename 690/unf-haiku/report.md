# Benchmark runs

## add_load_forecast run 1: passed


I added a Load named "Household" to the Home hub and confirmed it appears under Home with 12 entities.

- **Connection:** Switchboard, AC. This was already selected, and it is where household consumption sits.
- **Forecast:** I added two sensors, `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power` (the current value). The form combined them into one forecast line.
- **Shedding:** Left at its default.

Points where I hesitated or was unsure:

1. **Naming:** The default name was "Load". I renamed it to "Household" because that describes the sensor, but you may prefer another name.
2. **Two sensors in one Forecast field:** The field accepted both the forecast and the current value, and I added both as you asked. I did not check how HAEO uses the current-value sensor alongside the forecast, so I can't confirm the pairing is what you intended.
3. **Connection choice:** I kept Switchboard without changing it. I'm fairly sure it's right for a household load, but I didn't check it against your wiring.
4. **Shedding:** I didn't open it, so I can't say whether the household load should be sheddable.
5. **Verification:** I checked only that the load was created. I did not open the saved configuration to confirm both sensors are still attached.

## add_load_forecast run 2: passed


I added a Load named "Household" to the Home hub. It is connected to the Switchboard (AC) and takes both Sigen consumed-power sensors as its forecast input. The Home hub now lists a Household Load device with 12 entities.

Points where I hesitated, was unsure, or may have made a mistake:

1. **Load name:** The default was "Load". I renamed it to "Household" to match what it represents. That is a judgment call, and you can change it.
2. **Connection:** Switchboard (AC) was preselected. I kept it because household consumption sits on the AC side, but I did not check this against your wiring.
3. **Current sensor placement:** The form had only one "Forecast" field, with no separate field for a current value. I added `sensor.sigen_plant_consumed_power` to that same field, beside the forecast sensor. The preview then showed the current value for "now" and the forecast for later intervals. I assumed that is the intended way to combine them, but I did not confirm it in the HAEO docs, which I did not have.
4. **Shedding:** I left the Shedding section collapsed at its defaults. I did not look at what it controls, because you did not ask for it.
5. **Verification:** I confirmed the success message and the new device on the hub page. I did not reopen the Household load to check the saved forecast entries.

## add_load_forecast run 3: passed


I added a household load to the Home hub. It's named "Household", uses the Switchboard (AC) connection, and has both your Sigen consumed power sensors as its forecast input. The success dialog confirmed creation, and "Household" now appears under the Home hub.

**Points where I hesitated or was unsure:**

1. **Element type.** The integration page offers a "Load" element, and I used it for household consumption. I didn't find a more specific option, so this was my judgement call.
2. **Name.** The form defaulted to "Load". I renamed it to "Household" so it's distinguishable from the other elements.
3. **Connection.** Switchboard (AC) was pre-selected. A household load sits on the AC side, so I kept it, but I didn't change or check the alternatives.
4. **Where the current sensor goes.** The form has only one "Forecast" field, and it accepts several sensors. I didn't see a separate "current power" field, so I added `sensor.sigen_plant_consumed_power` alongside the forecast. Once I did, the preview switched "now" to 0.501 kW and kept the forecast for later intervals. I read that as the current reading replacing the forecast's present value, not being summed with it, but I inferred that from the preview only. The help text didn't say it explicitly.
5. **Shedding.** I left the Shedding section at its defaults without reading what it does. I didn't judge whether household load should be sheddable.
6. **Verification.** I confirmed the entry was created and that the Household device shows 12 entities. I did not check the individual entity values or how the optimiser uses this load.

## add_load_forecast run 4: passed


I added the household load to HAEO as a new Load element called "Household" under the Home hub. The success dialog confirmed it, and the Home hub now lists Household with 12 entities.

- **Connection:** Switchboard, AC (the default), since the household draws from the AC side.
- **Forecast:** `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power`, both in the same Forecast field. The combined preview shows now 0.501 kW, then 0 to 1.66 kW over 168 hours.
- **Shedding:** left at its default, which I did not change.

Where I hesitated or was unsure:

- **Load name:** I chose "Household" because the default was "Load" and the name should say what it is. You may prefer another name.
- **Connection choice:** I went with the default Switchboard, AC option without confirming it against your wiring. If the house loads sit behind the inverter, the Inverter option would be the right one.
- **Current sensor in the same field:** The form lets you add the current sensor next to the forecast, so I did that. I did not confirm how HAEO weights the two sources. The preview suggests the current reading anchors the first interval.
- **Shedding section:** I did not open it. I assumed the defaults suit a household load.
- **Verification depth:** I checked the device and entity count on the integration page but did not open the new entities to confirm their values.

## add_load_forecast run 5: passed


I added a Household load to the Home hub. It uses the Sigen consumed power forecast and the current consumed power sensor, and the new "Household" device appears under Home.

Here is what I set:
- **Name:** Household (the form defaulted to "Load"; I renamed it).
- **Connection:** Switchboard, AC (the default, which I kept because household consumption sits on the AC side).
- **Forecast:** `sensor.sigen_plant_consumed_power_forecast` plus `sensor.sigen_plant_consumed_power`. The form's combined preview then read "now 0.501 kW, then 0 kW to 1.66 kW over the next 168 hours", so the current sensor drives the present value and the forecast covers the future.
- **Shedding:** left unset.

I did not reopen the entry to confirm the saved forecast values.

Points where I hesitated or was unsure:
- **Two sensors in one Forecast field:** the form has no separate slot for the current sensor, so I added it to the same field. I inferred from the live preview that it sets the "now" value, but the help text never said so.
- **Renaming the load:** "Household" is my choice, not something you specified. It is easy to change later.
- **Connection choice:** I kept the Switchboard default without checking the help text for the other options. I believe it is right for household load.
- **Shedding:** I left it blank without deciding whether you want load shedding for household consumption.

## add_load_forecast run 6: passed


I added the household load as "Household" under the Switchboard connection, with both consumed-power sensors as its forecast input. HAEO confirmed "Created configuration for Household", and the hub now lists a Household device with 12 entities.

Where I hesitated or was unsure:

- **Name:** The default was "Load", which would be ambiguous next to the other elements. I renamed it to "Household". Rename it if you prefer something else.
- **Connection:** I kept the default, Switchboard (AC). I assumed the household draws from the AC side, which matches the usual setup, but I did not check your wiring.
- **Current sensor:** The Forecast field only offers one input type, so I added the current sensor "Sigen Plant Consumed Power" alongside the forecast sensor "Sigen Plant Consumed Power Forecast" rather than in a separate field. The combined preview then showed "now 0.501 kW, then 0 kW to 1.66 kW over 168 hours", which suggests the current value is used for the present interval. I did not verify how HAEO uses it internally.
- **Shedding:** I left that section collapsed at its defaults, since you didn't ask for it.
- **Verification:** I confirmed the load was created but did not open its entities to check their values.

## add_solar_forecast_solar run 1: passed


I added a Solar element to the Home hub with all 32 Forecast.Solar energy production sensors, and the Solar device now shows under the hub with 4 entities.

- **Connection:** I left the default "Inverter, DC", since the panels feed the inverter.
- **Forecast sensors:** For each direction (east, north, south, west) there are eight sensors: today, tomorrow, day after tomorrow, and 3 to 7 days from now. The picker's "Add all 32" added exactly those.
- **Name:** I kept the default name "Solar".
- **Curtailment:** I left this section alone.

Points where I hesitated or was unsure:
- The first search ("forecast") showed 33 results, including a Sigen Plant Consumed Power Forecast sensor. I did not use "Add all 33" because that sensor is not solar. I searched "energy_production" instead, which gave exactly 32 and excluded it.
- The South sensors are labelled "solar prediction" where the other directions say "solar production". The entity IDs follow the same `energy_production_*_south` pattern, so I treated them as Forecast.Solar, but I did not confirm the source integration of each sensor.
- I chose "Inverter, DC" from the connection options by reasoning about your setup, not from a stated preference in the task.
- I did not check the saved Solar entities or their values after finishing, so I have not confirmed that the forecasts are loading correctly.

## add_solar_forecast_solar run 2: passed


I added the solar element "Solar" to the Home hub with all 32 Forecast.Solar sensors. HAEO created it and it now appears in the hub's device list.

- **Connection:** Inverter (DC), the default. I read "feeds into your inverter" as DC-coupled panels behind the inverter. If your panels actually feed the AC side (Switchboard), this is the setting to change.
- **Sensors:** The picker listed 38 entities, but only 32 are Forecast.Solar. Those are `energy_production_*` for today, tomorrow and days 2–7 in each of East, North, South and West. I filtered the list to `energy_production` and used "Add all 32". I did not use "Add all 38", which would also have added six Sigen sensors.
- **Curtailment:** Left at its default because I had no information about it.
- **Name:** Left as "Solar".

I did not open the Solar device afterwards to confirm all 32 sensors were saved. The preview chart showed the combined forecast (0 kW now, up to 17.9 kW), and the success dialog confirmed creation.

Points where I hesitated or was unsure:
- The Connection choice was an inference from your description, not something the form made obvious. I'm least sure of this one.
- The South sensors are labelled "solar prediction forecast" while the others say "solar production forecast". I treated them as the same Forecast.Solar sensors because they share the `energy_production_*_south` naming.
- I did not check the sensor count on the saved element. The 32 I added came from the "Add all 32" count and the visible list.
- I used "Add all 32" on a filtered list rather than clicking sensors one at a time. That was faster, and I checked the result before submitting.
- The HAEO page shows 4 entities under the new Solar device. I did not look into what those four are.

## add_solar_forecast_solar run 3: passed


I added a Solar element to HAEO's Home hub with all 32 Forecast.Solar production sensors, and the Solar device now shows up under Home.

- **Connection:** I left it at "Inverter, DC", the default. You said the panels feed the inverter, so I took that as DC-coupled behind the inverter.
- **Forecast sensors:** I typed "energy_production" in the forecast picker, which narrowed it to exactly 32 entries (East, North, South and West, each with today, tomorrow, day after tomorrow, and 3 to 7 days out). I used "Add all 32" on that filtered list. The unfiltered "Add all" would have pulled in Sigen inverter sensors too.
- **Name:** "Solar" (the default).
- **Curtailment:** left at its default, which I did not change or review.
- **Result:** The success dialog said "Created configuration for Solar." The forecast preview shows about 17.9 kW peak over the next 168 hours. The Home hub now reports 7 devices and 60 entities.

Points where I hesitated or was unsure:
- I did not verify the Connection choice against your wiring. "Inverter, DC" is my reading of "feeds into your inverter," and it would be wrong if the panels are AC-coupled to the switchboard.
- The "Add all" button's count (38) was larger than the Forecast.Solar set. I only noticed that after reading the full list, so I had to filter first. A mistake there would have added Sigen sensors that are not solar forecasts.
- I did not open the Curtailment section, so I don't know whether it needs a setting for your installation.
- I did not check the new Solar entities' states or the optimizer output after submitting. I only confirmed that the configuration was created.

## add_solar_forecast_solar run 4: passed


I added the solar hub "Solar" to your Home HAEO setup, with all 32 Forecast.Solar energy sensors (east, north, south and west, each with today, tomorrow, day after tomorrow and 3 to 7 days out). The Solar device now appears under Home.

The Solar hub has 4 entities, which I did not inspect further, so I have not confirmed that the forecast data is being read correctly.

Points where I hesitated or was unsure:
- **Connection:** I kept the default "Inverter, DC", since you said the solar feeds the inverter. I did not look at the "Switchboard, AC" option in detail.
- **"Add all" count:** The picker's first "Add all" offered 38 options, which included Sigen sensors. I narrowed the search to `energy_production` first, which gave exactly 32, so I used that "Add all 32" and not the broader one. I checked the 32 names against the four directions but did not verify the sensor values.
- **Sensor naming:** Some sensors are labelled "solar production forecast" and the South ones "solar prediction forecast". I assumed both are the Forecast.Solar sensors, based on the `energy_production_*_south` entity IDs.
- **Name and curtailment:** I left the name as the default "Solar" and left Curtailment untouched, because I did not know what it should be for this setup.
- **Version:** The page shows HAEO version 0.5.1, and I did not check the docs for it.

## add_solar_forecast_solar run 5: passed


I added the solar element to HAEO as "Solar" with all 32 Forecast.Solar production sensors: 8 for each of east, north, south and west. The integration page now shows a Solar device with 4 entities.

**Points where I hesitated or was unsure:**

- **Connection:** I kept the default "Inverter, DC" because you said the panels feed the inverter. I did not check whether your inverter is DC-coupled to the battery. If the panels are wired to the AC side, "Switchboard, AC" would be the right choice instead.
- **Sensor selection:** The unfiltered picker offered "Add all 38". Six of those were Sigen sensors, not Forecast.Solar, so I typed `energy_production` to narrow the list to 32 before adding them. I then checked that the 32 matched the four directions with eight day-sensors each.
- **South naming:** The south sensors are labelled "solar prediction forecast" while the others say "solar production forecast". They have the same `energy_production_*_south` entity ID pattern, so I treated them as Forecast.Solar and included them. Worth a quick check.
- **Curtailment:** I left this collapsed at its default and did not look at it. I don't know whether your inverter needs a curtailment setting.
- **Name:** I kept the default name "Solar" without thinking about whether a different name would be clearer.
- **Verification:** I confirmed the device and entity count on the integration page, but did not open the Solar device to check the forecast values or the individual entity states.

## add_solar_forecast_solar run 6: passed


I added the solar element to the Home hub as "Solar", using all 32 Forecast.Solar energy production sensors. HAEO confirmed "Created configuration for Solar", and a Solar device with 4 entities now appears under the hub.

Settings:
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default), since the panels feed the inverter.
- **Forecast:** East, North, South and West, each with today, tomorrow, day after tomorrow and days 3 to 7 ahead. I filtered the picker to `energy_production` and used "Add all 32". The unfiltered "Add all 38" would also have pulled in Sigen plant sensors.
- **Curtailment:** left at its default.

Points where I hesitated or was unsure:
- **Connection choice:** I read "feeds into your inverter" as DC-coupled to the inverter, not AC at the switchboard. If the panels actually feed a separate AC inverter, this should be Switchboard instead.
- **Sensor scope:** I took "every day it covers" to mean all 8 sensors per direction, which made 32 in total. I did not check whether the "today" sensors are partial-day totals that HAEO handles differently. The combined preview on the form showed 0 kW now and up to 17.9 kW over 168 hours, which looked plausible, but I did not verify the numbers against your inverter.
- **Naming:** The South sensors are labelled "solar prediction forecast" while the others say "solar production forecast". I added them all anyway, since the request was for all of them.
- **Curtailment:** I didn't touch it because you didn't mention it, though it may matter if your inverter limits export.
- **Verification:** I confirmed creation through the success dialog and the device entity count. I did not open the new Solar element to check its saved forecast list.

## add_solar_solcast run 1: passed


The Solar element is added to your Home hub and the Solcast forecasts are attached to it.

- **Name:** Solar (default).
- **Connection:** Inverter, DC, since the panels feed the inverter.
- **Forecast:** `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`.

The Solar device now shows 4 entities under Home, and the integration page went from 6 to 7 devices and 57 to 61 entities. I did not inspect the new entities' values or the forecast curve beyond the preview on the form, which showed 0 kW now rising to 23.2 kW over 72 hours.

Points where I hesitated or was unsure:

1. **Connection choice:** I picked "Inverter, DC" because you said the panels feed the inverter. The alternative, "Switchboard, AC", would fit if the panels were on the AC side, so I went with your description.
2. **Forecast picker:** My second click on the forecast field did not open the dropdown, so I typed "solcast" to search. The search offered "Add all 2", which I used for the tomorrow and day 3 sensors. I checked the chips afterwards and all three were present.
3. **Curtailment:** This section is optional and I left it at its default. I did not review what it does, so I may have skipped a setting you would want.
4. **Name:** I kept the default name "Solar" without thinking about whether you wanted something more specific.

## add_solar_solcast run 2: passed


I added the rooftop solar to the Home hub as "Solar" and HAEO confirmed "Created configuration for Solar". The Home hub now shows a Solar device with 4 entities.

- **Connection:** left at "Inverter, DC", since the panels feed the inverter.
- **Forecast:** the three Solcast sensors (Forecast Today, Forecast Tomorrow, Forecast Day 3) are attached. The combined preview shows about 23.2 kW at peak over 72 hours.
- **Name and curtailment:** left at the defaults.

Points where I hesitated or was unsure:

1. **"Add all 3" versus picking one by one:** I used "Add all 3" because the search showed exactly the three Solcast forecast sensors. I did not check that no other Solcast sensors were hidden by the search filter.
2. **Connection choice:** I was unsure whether "Inverter, DC" or "Switchboard, AC" was right. I chose DC because you said the panels feed the inverter, and the default was already set to it.
3. **Name:** I kept "Solar" rather than something like "Rooftop Solar". It is a cosmetic choice I did not confirm with you.
4. **Curtailment:** I left it at the default without reading what it does. I did not open it, so I do not know whether it needs configuring for your setup.
5. **Verification:** I confirmed success from the dialog and the new device entry. I did not reopen the Solar element to check that the three forecast sensors were saved.

## add_solar_solcast run 3: passed


The Solar element is added to the Home hub. It uses the Inverter (DC) connection and the three Solcast PV forecast sensors. HAEO reports "Created configuration for Solar", and the Home hub now shows a Solar device with 4 entities. I didn't reopen the element to confirm the saved forecast values.

Points where I hesitated or was unsure:

1. **Connection choice:** The form offered "Inverter, DC" and "Switchboard, AC". I picked Inverter because you said the panels feed the inverter. I kept the default rather than checking how HAEO's energy flows are modelled, since I can't read its docs.
2. **Forecast sensors:** The picker offered "Add all 3", and I used it. Its list also showed unrelated sensors such as the Sigen plant power readings. I picked only the Solcast entries, which are Forecast Today, Forecast Tomorrow and Forecast Day 3. I didn't check whether Solcast also provides other PV sensors that should be included.
3. **Name:** I left the name as the default "Solar". You didn't ask for a specific name, so this is a guess.
4. **Curtailment:** This section was collapsed and I left it at its default. I didn't open it to see what it offers, so I don't know whether any curtailment setting should apply to your panels.
5. **Verification:** I didn't reopen the saved Solar configuration to check the stored connection and forecast values. I relied on the success message and the new entity count.

## add_solar_solcast run 4: passed


I added the solar element to the Home hub and it's now listed as a "Solar" device with 4 entities. The count went from 57 to 61 entities.

Settings I chose:
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default). Your panels feed the inverter, so this is the right connection.
- **Forecast:** all three Solcast sensors, added with "Add all 3": `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`. The preview showed a combined forecast of 0 kW now, rising to 23.2 kW over the next 72 hours.
- **Curtailment:** left at default, since you didn't ask for it.

I didn't open the new Solar device afterwards to confirm its entity values, so the check that it took effect is the entity count and the success dialog.

Where I hesitated or was unsure:
- I wasn't sure whether the Solcast sensors should be added as three separate forecasts or as one combined list. I used "Add all 3" because the three sensors together make up one PV forecast over time.
- I left Curtailment alone. I didn't check whether it matters for a rooftop system that sends its surplus to the grid, so it may need a look.
- The Connection choice relied on the label "Inverter, DC" matching your wiring. I didn't have a wiring diagram to confirm it.

## add_solar_solcast run 5: passed


I added the Solar element to the Home hub and it was created. The Solar device now appears under Home with 4 entities.

- **Name:** left as the default, "Solar".
- **Connection:** "Inverter, DC", which is the default. Your panels feed the inverter, so I kept this rather than "Switchboard, AC".
- **Forecast:** I used "Add all 3" to add the Solcast sensors for Today, Tomorrow and Day 3. The forecast preview showed a combined curve reaching about 23.2 kW.
- **Curtailment:** left unconfigured.

Points where I hesitated or might have gone wrong:

1. **Connection choice:** I chose "Inverter, DC" from the panels' physical wiring. I did not check how HAEO's model uses the two options, so if your inverter is actually on the AC side, this would need changing.
2. **Name:** I kept "Solar" without thinking about whether a more specific name would help if you add more arrays later.
3. **Curtailment:** I skipped this section without reading its help text. It is probably optional, but I did not confirm that.
4. **Forecast entities:** I picked all three Solcast sensors, as you asked, but did not check whether HAEO expects one combined forecast or accepts several.
5. **Verification:** I confirmed the Solar device exists, but I did not open its entities to check the values.

## add_solar_solcast run 6: passed


I added the solar array to Home as a Solar element named "Solar", using the three Solcast forecast sensors. The Solar device now appears under Home with 4 entities.

Settings:
- **Name:** Solar (default, left as is)
- **Connection:** Inverter, DC (default). Your panels feed the inverter, so I kept this.
- **Forecast:** `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`. The preview shows the combined forecast peaking at about 23.2 kW.
- **Curtailment:** left at defaults.

I did not re-open the Solar element afterwards to confirm the saved values, so the three forecast entries are confirmed only from the form before submit.

Points where I hesitated or was unsure:
1. I was not certain whether HAEO wants the Solcast sensors as separate entries or a single one. I added all three because the picker offered them and you asked for all three days.
2. The first click on the Today option closed the picker and did not stay open for a second selection, so I re-opened it and typed "solcast" to find the other two. I then used "Add all 2", which added Tomorrow and Day 3 together. That is a small risk of adding something unintended, but the list showed exactly those two.
3. I chose "Inverter, DC" for the connection without looking at the help text, because your description (panels feed the inverter) matched that option's label. I did not confirm the meaning from any documentation.
4. I left Curtailment alone. You did not mention it, and I had no basis to change it.
5. The Solar name stayed "Solar". That is a default I accepted without thinking about whether you wanted a different label.

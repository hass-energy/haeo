# Benchmark runs

## add_load_forecast run 1: passed


I added a Load to the Home hub, using both Sigen sensors. It now shows under Home with 1 device and 12 entities. I didn't open the new device's entities or check any of their values.

- **Sensors:** I picked `sensor.sigen_plant_consumed_power_forecast` (the forecast) and `sensor.sigen_plant_consumed_power` (the current reading). The Forecast field accepted both together.
- **Connection:** the Load is connected to the Switchboard. That was already selected by default, and I left it. It seemed right for whole-house consumption.
- **Name:** I kept the default name "Load".

Where I hesitated or was unsure:
- **One field for both sensors:** the Forecast field is the only place to enter sensors, and it's labelled for forecasts. I wasn't sure it would accept the current-power sensor as well. It did, and the preview showed a combined "now 0.501 kW, then …" line.
- **Switchboard vs Inverter:** I wasn't certain Switchboard was better than Inverter. I assumed it was because household consumption sits on the AC side.
- **Name left as default:** I didn't give the Load a more descriptive name, such as "Household".
- **Shedding section:** I didn't open it, so I don't know what it does or whether the defaults suit you.

## add_load_forecast run 2: passed


I added the household load to HAEO. A Load element now appears under Home, with 12 entities. It's named "Load" (the default name, which I didn't change) and connected to the Switchboard. I didn't open it again afterwards to check its settings.

In its Forecast field I picked two sensors:
- Sigen Plant Consumed Power Forecast
- Sigen Plant Consumed Power, the current reading

The field accepted both. The preview then showed "now 0.501 kW, then 0 kW to 1.66 kW over the next 168 hours".

Where I hesitated or was unsure:
- **Current sensor:** There was no separate field for the current consumed power sensor. I assumed the Forecast field was meant to hold both sensors, and I added the current one there. The preview's "now" value changed from 0.4 kW to 0.501 kW when I added it, which suggests it took effect.
- **Connection:** I left Switchboard selected, as it was by default. I didn't check whether it was the right place for the household load, though it seems sensible for whole-home consumption.
- **Shedding:** I didn't open the Shedding section and left it at its defaults.

## add_load_forecast run 3: passed


I added a Load named "Load" to the Home hub. It now appears in the hub's list of parts. I didn't open it afterwards to re-check its settings.

- **Connection:** Switchboard (AC). It was already selected, and a household load fits there.
- **Forecast field:** I picked both `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power`, the current reading. The field took both sensors. The preview chart showed "now 0.501 kW", so the current reading was being used.

Where I hesitated or was unsure:
- I kept the default name "Load" rather than renaming it.
- I wasn't sure whether the Forecast field would accept two sensors. It did, but I don't know how HAEO combines them. The chart labelled them "Combined".
- I left the "Shedding" section alone because you didn't ask for it.

## add_load_forecast run 4: passed


I added a load called "Load" to HAEO. It uses both Sigenergy sensors: Sigen Plant Consumed Power Forecast and the current Sigen Plant Consumed Power. HAEO now lists it as a new device with 12 entities.

I didn't open the new load afterwards to check the saved settings. The only checks were the "Created configuration for Load" message and the device appearing on the integration page.

I connected it to the Switchboard, which was already selected by default. I kept it because a household load sits on the AC side.

The form's Forecast field accepts several sensors, so I added both there. Its preview showed "now 0.501 kW", which matches the current sensor, and the forecast ranging up to 1.66 kW over the next 168 hours.

Points where I hesitated:
- **Connection:** I accepted the Switchboard default without comparing it to the Inverter option.
- **Name:** I kept the default name "Load" rather than something like "House".
- **Combining two sensors:** The form has no separate field for a current-power sensor, so I used the one Forecast field for both. The preview suggests HAEO combines them, but I don't know exactly how.
- **Optional settings:** I left the "Shedding" section collapsed and unchanged.

## add_load_forecast run 5: passed


I added a load named "Load" to HAEO and connected it to the Switchboard. After I submitted it, the Load device showed up under the Home hub with 12 entities.

In the single Forecast field I picked both Sigen sensors:
- **Sigen Plant Consumed Power Forecast:** the consumed power forecast.
- **Sigen Plant Consumed Power:** the current consumed power sensor, which read 0.501 kW.

The field accepts several sensors, and its preview showed the combined result as "now 0.501 kW, then 0 kW to 1.66 kW over the next 168 hours." I didn't open the new load afterwards to check the saved settings.

Points where I hesitated or was unsure:
- **Connection:** I kept the default Switchboard connection without checking it, because a household load normally hangs off the AC side. I didn't choose Inverter.
- **Name:** I kept the default name "Load" rather than something like "Household".
- **One field for both sensors:** There was no separate field for the current sensor, so I assumed putting both in Forecast was the intended way. The preview updating with both is my only evidence.
- **Shedding:** I left the Shedding section collapsed and unchanged.

## add_load_forecast run 6: passed


I added a Load named "Household" to the Home hub. It connects to the Switchboard and uses two Sigenergy sensors:
- `sensor.sigen_plant_consumed_power_forecast`, the consumed power forecast.
- `sensor.sigen_plant_consumed_power`, the current consumed power.

HAEO showed "Created configuration for Household", and the load now appears under the hub with 12 entities. I didn't check any of those entities' values.

Points where I hesitated or guessed:
- **Connection:** The form had Switchboard selected by default. I kept it because household consumption is a normal AC load, but I didn't check that against your wiring.
- **Name:** I changed the default "Load" to "Household". You didn't give a name, so this was my choice.
- **Single field:** The form had only one "Forecast" field, so I put the current sensor in it next to the forecast sensor. I assumed that's how HAEO wants both used. The form's preview showed a combined result starting at 0.501 kW now, which suggests it worked.
- **Shedding:** I left the optional "Shedding" section collapsed and didn't look at it.

## add_solar_forecast_solar run 1: passed


I added a Solar element to the "Home" hub, connected to the Inverter, with all 32 Forecast.Solar sensors. That is 8 sensors for each of east, north, south and west: today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element again to check its saved settings.

I left the connection on the default, Inverter. Your panels feed into the inverter, so that matched.

Points where I hesitated:
- **"Add all" button:** With an empty search it offered 38 entities, which included Sigen Plant sensors that aren't Forecast.Solar. I typed "energy_production" first, so the button added exactly the 32 forecast sensors.
- **South sensor names:** The south sensors are named "South solar prediction forecast" while the others say "production forecast". Their entity IDs follow the same `energy_production_*_south` pattern, so I included them.

## add_solar_forecast_solar run 2: passed


I added a "Solar" element to HAEO and connected it to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors per direction. Those 8 are today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and I counted 32 entries in the forecast field before submitting.

I didn't reopen the Solar element afterwards to check the saved values.

Points where I hesitated or could have gone wrong:
- **Connection:** I kept the default, Inverter, and didn't change it. The picture for that option showed Battery and a sun icon, which matches panels feeding the inverter. The other option was Switchboard.
- **"Add all":** The unfiltered picker offered "Add all 38". That count also included Sigen Plant sensors, such as PV power and consumed power. I typed "energy_production" first, so "Add all" covered exactly 32 sensors.
- **Curtailment:** I left the Curtailment section closed and untouched. I wasn't asked about it.

## add_solar_forecast_solar run 3: passed


I added a Solar element to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors each. For each direction those are today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element again after saving to check its settings.

I chose Inverter (DC) as the connection because it was already selected and your panels feed the inverter. I left the Curtailment section alone.

Points where I hesitated or was unsure:
- **"Add all" count:** With no search text, "Add all" offered 38 sensors. The extra 6 were Sigen plant sensors, which aren't Forecast.Solar. I typed "energy_production" into the search first, which narrowed the list to 32, and then used "Add all".
- **South sensor names:** The south sensors are named "South solar prediction forecast" rather than "solar production forecast". Their entity IDs match the others, so I included them.
- **Combined forecast chart:** After adding the sensors, the dialog showed a combined forecast chart (0 kW to 17.9 kW over the next 168 hours). I took that as a sign they were read correctly but didn't check it further.

## add_solar_forecast_solar run 4: passed


I added a Solar element to HAEO. It connects to the Inverter (DC) and uses all 32 Forecast.Solar sensors. That is 8 sensors for each of east, north, south and west: today, tomorrow, the day after tomorrow, and 3 to 7 days from now.

I confirmed the dialog showed "Created configuration for Solar." and that Solar now appears on the integration page. I did not open it again to check the saved values.

Points where I hesitated or was unsure:
- **Connection:** I left the default, Inverter (DC), because you said the panels feed into your inverter. I didn't check whether the other option, Switchboard (AC), would suit your wiring better.
- **Picking the sensors:** The first "Add all" button said 38 and would have included six Sigen Plant sensors that aren't Forecast.Solar. I typed "energy_production" to filter the list first, so "Add all" said 32. I then counted 32 entries in the field and none were Sigen.
- **Curtailment:** I left that section unopened and unchanged.

## add_solar_forecast_solar run 5: passed


I added Solar to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors. That's east, north, south and west, each for today, tomorrow, the day after tomorrow and days 3 to 7. Home Assistant showed "Created configuration for Solar", and Solar now appears in the hub list. I didn't open the new entry to check its settings.

Points where I hesitated or took a risk:
- **"Add all" button:** With nothing typed, the picker offered "Add all 38". The extra six were Sigen Plant sensors (consumed power, PV power and so on), which aren't Forecast.Solar sensors. I typed "energy_production" first, so the button became "Add all 32". I checked that all 32 were the East, North, South and West forecast sensors, then clicked it. I also counted 32 remove buttons in the field before submitting.
- **Connection:** I left the connection on Inverter (DC), which was already selected. It matches rooftop solar feeding the inverter. I didn't change it or look at the Switchboard option beyond reading the label.
- **Name and other settings:** I kept the default name "Solar". I left the Curtailment section closed and untouched.

## add_solar_forecast_solar run 6: passed


I added a Solar element to HAEO. It uses all 32 Forecast.Solar estimated energy production sensors: east, north, south and west, for each of the 8 days (today, tomorrow, day after tomorrow, and 3 to 7 days from now). HAEO confirmed "Created configuration for Solar", and Solar now appears under Home.

I didn't reopen the Solar element to check the saved sensor list, so the 32 rests on the "Add all 32" count and the confirmation message.

I left the connection at its default, Inverter (DC), since the panels feed into your inverter.

Points where I hesitated or was unsure:
- **Sensor selection:** The picker's "Add all" button first offered 38 sensors, which included unrelated Sigen Plant sensors. I typed "energy_production" into the search box first, so "Add all" then covered only the 32 Forecast.Solar sensors.
- **Connection default:** I accepted the default without trying the other option, Switchboard (AC).
- **Optional sections:** I didn't open the Curtailment section.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub, connected to the Inverter, and gave it all three Solcast forecast sensors: Today, Tomorrow and Day 3. After I submitted, the Solar device showed up with 4 entities. The hub went from 6 to 7 devices.

The form's forecast preview showed a combined forecast of 0 kW now, then 0 to 23.2 kW over the next 72 hours.

I didn't open the new Solar entry again after saving to check its saved settings. I also left the Curtailment section alone.

Points where I hesitated or was unsure:
- **Connection:** The form already had Inverter (DC) selected, and I kept it because the panels feed the inverter. The other choice was Switchboard (AC).
- **Forecast sensors:** Searching "solcast" listed exactly three sensors, so I used "Add all 3" instead of picking them one by one. I assumed HAEO combines them into one forecast. The preview's combined 72-hour line suggests it does, but I didn't confirm it.
- **Name:** I kept the default name "Solar".

## add_solar_solcast run 2: passed


I added a Solar element named "Solar" to the Home hub. The integration page now lists it as a device with 4 entities. I didn't open the new element again to check its saved settings.

- **Connection:** Inverter, which was already selected by default.
- **Forecast:** the three Solcast sensors, `sensor.solcast_pv_forecast_forecast_today`, `…_tomorrow` and `…_day_3`. The form's combined preview showed 0 kW now, rising to 23.2 kW over the next 72 hours.
- **Curtailment:** I left this section collapsed and unchanged.

Points where I hesitated or made a mistake:
- After picking the Today sensor, the dropdown didn't reopen when I clicked the field again. I typed "solcast" to search and used "Add all 2" to add the other two.
- I didn't set Curtailment because the task didn't mention it.

## add_solar_solcast run 3: passed


I added a Solar element named "Solar" to Home. It connects to the Inverter, and its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar". The Home hub now lists a Solar device with 4 entities.

The forecast chart in the dialog showed a combined 0 kW now, rising to 23.2 kW over the next 72 hours. I didn't open the new element again after saving.

Points where I hesitated or made a mistake:
- **Connection:** the form had Inverter selected by default and I left it. I took that to be right, since your panels feed the inverter.
- **Forecast picker:** after I picked the first sensor, clicking the field again didn't open the list. I typed "Solcast" to bring up the other two, then used "Add all 2".
- **Curtailment:** I didn't open that section and left it at its defaults.

## add_solar_solcast run 4: passed


I added a Solar element to the Home hub. It's connected to the Inverter and uses all three Solcast PV Forecast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3.

I checked that it took effect. The form showed a combined forecast preview, "now 0 kW, then 0 kW to 23.2 kW over the next 72 hours". HAEO then said "Created configuration for Solar", and Solar now appears under Home with 4 entities.

Points where I hesitated or was unsure:
- **Connection:** the form already had Inverter (DC) selected, and I left it. That matches your panels feeding the inverter.
- **"Add all 3":** after typing "solcast" in the forecast picker, I used the "Add all 3" option rather than picking each sensor. I confirmed afterwards that all three were listed.
- **Curtailment:** I didn't open the Curtailment section and left it at its defaults.

I made no mistakes that I'm aware of.

## add_solar_solcast run 5: passed


I added a Solar element to the Home hub and connected it to the Inverter. Its forecast uses all three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears under Home.

I left the Curtailment section alone.

Points where I hesitated or went off course:
- **Connection:** The form had Inverter pre-selected, so I kept it. That matches your panels feeding the inverter, and it's the DC connection rather than the Switchboard (AC) one.
- **Forecast picker:** After I picked the first sensor, the list closed and clicking the field again didn't reopen it. I typed "Solcast" to bring it back, then used "Add all 2" to add the other two.

## add_solar_solcast run 6: passed


I added a Solar element to the "Home" hub and connected it to the Inverter. Its forecast uses all three Solcast sensors: Today, Tomorrow and Day 3. After I submitted it, Solar appeared in the hub list as its own device with 4 entities.

I didn't open the new Solar entry again to check the saved settings. I also didn't touch the optional Curtailment section.

Points where I hesitated or made a mistake:
- **Connection:** "Inverter" was already selected by default, and it matched your setup, so I left it. I didn't try "Switchboard".
- **Forecast picker:** After I picked the first sensor (Today), the dropdown closed. My next click reopened nothing, so I typed "Solcast" to bring the list back. Then I used "Add all 2" to add Tomorrow and Day 3.
- **Name:** I kept the default name "Solar".

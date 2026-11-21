# Benchmark runs

## add_solar_forecast_solar run 1: passed


I added a Solar element to HAEO and the interface confirmed "Created configuration for Solar." It's connected to the Inverter and uses all 32 Forecast.Solar sensors as its forecast. That is the east, north, south and west sensors, each with eight days: today, tomorrow, the day after tomorrow, and 3 to 7 days from now. The Solar entry now shows in the Home hub's list. I didn't open it again afterwards to check the saved settings.

Points where I hesitated or was unsure:
- **Connection:** "Inverter" (DC) was already selected as the default. I kept it because you said the panels feed into your inverter. I didn't test the other choice, "Switchboard".
- **Picking sensors:** Choosing sensors one at a time closed the list after each pick. I typed `energy_production_` in the search box and used the "Select all 32" option instead. I checked that this matched only the Forecast.Solar sensors and not the Solcast or Sigen ones. I also counted 32 selected entries before submitting.
- **Curtailment:** I left the collapsed Curtailment section alone, since you didn't mention it.

## add_solar_forecast_solar run 2: passed


I added Solar to HAEO. It uses all 32 Forecast.Solar sensors: east, north, south and west, each for today, tomorrow, the day after tomorrow, and days 3–7. HAEO showed "Created configuration for Solar." I didn't reopen the Solar entry to check its saved settings. After clicking Finish, I only confirmed that Solar now appears on the integration page.

I left the connection on the default, Inverter (DC). Your solar feeds the inverter, so that matched.

Points where I hesitated or made mistakes:
- **Blocked commands:** Two of my commands were denied, a shell loop and a pipeline that checked for duplicates. I wrote the steps out one by one instead.
- **Parallel batches:** I ran the south and west batches at the same time. Both finished correctly, but that was luck, since the order of the steps could have mattered.
- **Duplicate check:** The duplicate check was denied, so I counted the selected sensors instead. The count was 32, and each sensor was picked by a unique search, so duplicates are unlikely.
- **Sensor choice:** The picker lists the Solcast sensors and Sigen sensors too. I assumed "all of those Forecast.Solar sensors" meant only the `energy_production_*` ones, so I left those out.
- **Picker behaviour:** The picker closes after each pick. I found that typing the sensor name and pressing Enter selects it.

## add_solar_forecast_solar run 3: passed


I added a Solar element to HAEO. It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors per direction. Each direction covers today, tomorrow, the day after tomorrow and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears in the Home hub's device list. I didn't open the saved element again to re-check its settings.

I connected it to the Inverter (DC), which was already selected by default. That fits panels that feed into your inverter.

Points where I hesitated or slipped:
- **Picking sensors:** The first click on a single sensor closed the dropdown after one pick. I then found that typing a direction name offers a "Select all 8" option, and I used that for each direction.
- **Other forecasts:** The picker also lists Solcast PV forecast sensors. I left them out because you asked for the Forecast.Solar ones only.
- **Sensor names:** The south sensors are named "solar prediction forecast" while the others say "solar production forecast". I took them as the same Forecast.Solar set because the entity IDs follow the same `energy_production_*_south` pattern.
- **Other settings:** I left the Curtailment section and the default name "Solar" alone.

## add_solar_solcast run 1: passed


I added a Solar element to the Home hub, connected to the Inverter. It uses the three Solcast sensors for its forecast: Forecast Today, Forecast Tomorrow and Forecast Day 3. After I submitted, HAEO showed "Created configuration for Solar". The hub now lists Solar as a device with 4 entities.

I didn't open the new element again to check the saved settings, and I didn't leave the integration page.

Points where I hesitated or was unsure:
- **Connection:** "Inverter" was already selected by default. I kept it because you said the panels feed into the inverter.
- **Forecast picker:** It let me tick several sensors, and the list also held many similar-looking "energy production" sensors for East, North, South and West. I searched for "solcast" to choose the right three.
- **Day 3 sensor:** The Solcast sensor is named "Forecast Day 3". I took it as the day-3 sensor you meant.
- **Curtailment:** I left the section collapsed and unchanged, since you didn't mention it.

## add_solar_solcast run 2: passed


I added a Solar element to HAEO and connected it to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and I clicked Finish. I didn't reopen the Solar element afterwards to check the saved values.

I left the name as the default "Solar" and didn't touch the Curtailment section.

Points where I hesitated or made mistakes:
- **Connection:** "Inverter" was already selected, which matches your setup, so I didn't change it.
- **Forecast picker:** It lets you pick several sensors. After I picked the first one, the list closed, so I had to search for "solcast" to reopen it.
- **Missed Tomorrow sensor:** My first attempt to add Tomorrow didn't register because I used a stale reference. I only saw it was missing when I checked the selections. I then searched again and added it.

## add_solar_solcast run 3: passed


Solar is now in HAEO, connected to the Inverter. Its forecast uses the three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. I reopened the saved Solar entry afterwards and all three were listed.

Points where I hesitated or slipped:
- The Connection field already had Inverter selected, so I left it. I took that as correct because your panels feed the inverter.
- The forecast picker also offered many other forecast sensors (East, North, South and West production forecasts). I ignored those and picked only the sensors named "Solcast PV Forecast".
- I clicked Submit without first checking that Day 3 had been added. I only confirmed it afterwards by reopening the saved entry.

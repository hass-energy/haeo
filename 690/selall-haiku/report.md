# Benchmark runs

## add_solar_forecast_solar run 1: passed


I added the solar element to the Home hub as "Solar", using all 32 Forecast.Solar sensors. HAEO reported "Created configuration for Solar", and the Home hub now shows a Solar device with 4 entities.

- **Connection:** Inverter, DC (the default). You said the panels feed the inverter, so I kept that.
- **Forecast:** I typed `energy_production_` in the picker, which returned exactly 32 matches, and used "Select all." That is eight days (today, tomorrow, and days 2 to 7) for each of East, North, South and West. Solcast and Sigen sensors were not included.
- **Curtailment:** Left at its default.

Points where I hesitated or was unsure:
- I chose "Inverter, DC" over "Switchboard, AC" based on your description. If the panels are actually wired to the AC side, the Switchboard option would be the right one. I did not verify your wiring.
- I used "Select all" on the filtered list without opening each sensor. I checked the names and the four directions, but I did not confirm the values, so a non-Forecast.Solar sensor with a matching name would have been included. The list only showed Forecast.Solar-style names.
- The solar name "Solar" is the default. I did not rename it.
- I did not open the new Solar element afterwards to confirm all 32 sensors were saved. I relied on the success message and the entity count.
- I did not check the Curtailment section, so I don't know whether it needs configuring for your setup.

## add_solar_forecast_solar run 2: passed


I added the solar element to the Home hub, using all 32 Forecast.Solar sensors.

**What was set up**
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default). Your panels feed the inverter, so this is the option that matches. I did not change it.
- **Forecast:** the 32 `energy_production_*` sensors, which are 4 directions (east, north, south, west) × 8 days (today, tomorrow, and day after tomorrow through day 7). I picked them with the picker's "Select all 32" option after filtering on `energy_production`.
- **Curtailment:** left at its default because you didn't ask for it.

The submit succeeded ("Created configuration for Solar"). The Home hub now lists a Solar device with 4 entities, and the integration's entity count went from 56 to 60.

**Where I hesitated or was unsure**
- **Connection choice:** I picked "Inverter, DC" because your panels feed the inverter. If the panels are actually wired to the AC side (the switchboard), "Switchboard, AC" would be the right choice instead. I did not verify your wiring.
- **Sensor filter:** Filtering on `energy_production` returned exactly 32 sensors, all from the four directions. Other forecast sensors were visible too (Solcast, Sigen). I left those out because they aren't Forecast.Solar.
- **Curtailment:** I did not open or change it. You may want to check it if your inverter limits export.
- **Entity count:** I confirmed the 4 new entities on the hub's summary, but I did not open the Solar device's entities to check their values or states.

## add_solar_forecast_solar run 3: passed


I added the Solar element to HAEO with all 32 Forecast.Solar energy production sensors. The "Created configuration for Solar" success dialog appeared, and the Home hub now lists a Solar device with 4 entities. I did not reopen the saved configuration to confirm all 32 forecasts were stored, so that check is still open.

What I set:
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default). Your panels feed the inverter, so this is the right choice.
- **Forecast:** I typed "energy_production" into the picker and used "Select all 32". That covers today, tomorrow, and days 2–7 for each of the four directions (East, North, South, West). The chips showed all 32 before I submitted.
- **Curtailment:** left at its default.

Points where I hesitated or was unsure:
1. **Connection choice:** I chose "Inverter, DC" because the panels feed the inverter. I did not check whether your system is DC-coupled or AC-coupled. If the panels sit on the AC side, "Switchboard, AC" would be the right choice instead.
2. **South sensors:** The South sensors are named "solar prediction forecast" rather than "solar production forecast". Their entity IDs follow the same `energy_production_*_south` pattern as the others, so I assumed they are also Forecast.Solar. I did not confirm the source.
3. **"Every day it covers":** I included today, tomorrow, and the day-2 to day-7 sensors, which is 8 per direction. I took "every day" to mean all of those. I did not include the Solcast or Sigen sensors, since they are not Forecast.Solar.
4. **Curtailment:** I did not look at this section or decide whether solar curtailment applies to your system. I left it at the default.
5. **Verification:** I did not reopen the Solar configuration after saving, so I have not confirmed that all 32 forecast entries were saved.

## add_solar_solcast run 1: passed


I added the rooftop solar to HAEO under the Home hub and pointed it at your three Solcast sensors. The integration now lists a new Solar device with 4 entities.

What I set:
- **Name:** Solar (the default)
- **Connection:** Inverter, DC. The panels feed the inverter, so I chose the inverter option rather than Switchboard.
- **Forecast:** `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`, added with the "Select all 3" option after filtering on "solcast".
- **Curtailment:** left at its default, since I had no reason to change it.

I did not reopen the Solar device afterwards to confirm the saved forecast sensors, so that check is still open.

Points where I hesitated or was unsure:
- The Forecast field lists many sensors, including other solar forecasts (East, North, South, West) and Sigen sensors. I deliberately filtered to Solcast so only your Solcast sensors were chosen.
- I chose "Inverter, DC" over "Switchboard, AC". The dialog's wording was the only guide, and I reasoned from your description that panels on the inverter are DC-coupled.
- I did not expand the Curtailment section, so I did not look at its options or whether it needs anything. I assumed it is optional.
- My first click on the Solar button opened the dialog without a visible change, so I took a screenshot to confirm it had opened before continuing.

## add_solar_solcast run 2: passed


I added the rooftop solar to HAEO under your Home hub, using the three Solcast forecast sensors. The Home hub now lists a Solar element with 4 entities.

What I set:
- **Name:** Solar (the default).
- **Connection:** Inverter, DC (the default). The panels feed the inverter, so this is the right choice.
- **Forecast:** `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`.
- **Curtailment:** "Allow curtailment" left at its default of On (fixed value).

I did not check the new entities' values after saving.

Points where I hesitated, were unsure, or made a mistake:
- **Forecast picker:** The list also offered other solar forecast sensors (East, North, South, West and Sigen). I used only the Solcast ones, since you asked for Solcast.
- **"Select all 3" shortcut:** I did not use it. I added the three sensors one at a time instead.
- **Stale-ref errors:** The picker closes after each selection, so my second and third clicks failed on stale element refs. Nothing was changed by those failures; I reopened the picker, searched again and selected the remaining sensors.
- **Curtailment:** It is a required field, and I accepted its default of On without reading any help text, since none was shown. I have not checked what it does to the solar output. You may want to confirm that setting suits your system.
- **Solar name:** I kept "Solar" without asking whether you wanted a different name.

## add_solar_solcast run 3: passed


The Solar element is added to your Home hub and saved as "Solar". The Solar device now shows under Home with 4 entities.

- **Name:** Solar (the default).
- **Connection:** Inverter, DC. I chose this because the panels feed the inverter directly.
- **Forecast:** All three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. I used the picker's "Select all 3" option.
- **Curtailment:** Left at its defaults.

I did not reopen the Solar configuration after saving to check the stored values.

Points where I hesitated or was unsure:
- **Connection choice:** I picked Inverter (DC) over Switchboard (AC). That follows from the panels feeding the inverter, but I'm inferring the wiring from your description rather than checking your hardware.
- **Curtailment:** I didn't open this section. It's optional, but if your inverter limits solar export, it may need configuring.
- **Solcast sensors:** I took "Select all 3" as covering today, tomorrow and day 3. The three selected entries matched the names you gave, so I believe it's correct.
- **Verification:** I confirmed the save from the success message and the new device count, not by reopening the saved form.

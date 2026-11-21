# Benchmark runs

## add_load_forecast run 1: passed


I added a "Household" load to the Home hub. It is connected to the Switchboard and takes both Sigen consumption sensors in its Forecast field. The integration reports "Created configuration for Household", and the Home hub now lists a Household load with 12 entities.

Points where I hesitated or may have gone wrong:

- **Current sensor placement:** The form had no separate field for a current power reading. The only place for power inputs was the Forecast entity list, so I added `sensor.sigen_plant_consumed_power` next to `sensor.sigen_plant_consumed_power_forecast` there. I am not sure HAEO treats the current sensor as the "now" value in that list. It may be treated as a second forecast source, which could double-count consumption. I did not verify how the optimizer uses it.
- **Connection choice:** The form offered Inverter (the default) and Switchboard. I picked Switchboard because the household draws from the home bus, not directly from the inverter. This is my reading of the labels, not something the help text confirmed.
- **Load name:** I renamed the default "Load" to "Household" for clarity. This was a judgement call and is easy to change.
- **Shedding section:** I opened it by accident and did not look at its settings. I left it at its defaults.
- **Submit clicks:** The first Submit click only closed the entity picker and did not submit. I clicked Submit again, which created the load.
- **Outputs not checked:** I did not open the new entities to confirm the forecast values are being read correctly.

## add_load_forecast run 2: passed


I added a "Household" load to the Home hub, connected to the Switchboard, with both Sigen consumed-power sensors in its Forecast field. HAEO confirmed "Created configuration for Household," and the Household device now appears under Home with 12 entities.

Where I hesitated:

1. **Load name.** You didn't give one, so I used "Household."
2. **Connection.** The dialog defaulted to Inverter. I chose Switchboard because household consumption sits on the house-side bus, not on the inverter's DC side. If your Sigen wiring puts the load behind the inverter, this should be changed.
3. **Where the current sensor went.** The load form has no separate field for a current power sensor. The only sensor slot is the Forecast list, so I added `sensor.sigen_plant_consumed_power` next to `sensor.sigen_plant_consumed_power_forecast`. I can't see how HAEO combines the entries in that list. If it adds them together, household load is double-counted, which is the main risk here. I did not verify the combined value.
4. **Shedding.** I left "Allow shedding" and "Consumption cost" at their defaults because you didn't ask about them.
5. **Constant-value field.** The Forecast field showed a kW number box above the entity picker. I left it empty and used only entities, since you asked for sensors.

## add_load_forecast run 3: failed

- $.forecast.forecast.value: expected the items ['sensor.sigen_plant_consumed_power_forecast', 'sensor.sigen_plant_consumed_power'] in any order, found ['sensor.sigen_plant_consumed_power_forecast']

I added the household load, but only partly: the current consumed power sensor is not in it.

**What's set up:**
- A new Load element named **Household** under the Home hub.
- Connection: **Switchboard**. I picked this because household consumption sits on the house bus alongside grid, battery and solar, not on the inverter.
- Forecast: **sensor.sigen_plant_consumed_power_forecast** (Sigen Plant Consumed Power Forecast).
- The load was created successfully and the Home hub now shows it with 12 entities.

**What's missing:**
- **sensor.sigen_plant_consumed_power** (the current reading) is not attached. The load form only has a Forecast sensor list, a Shedding section and a constant kW field, and none of them is a slot for a live reading. I did not add the current sensor to the Forecast list because that would mix a live value into the forecast series. You'll need to decide where HAEO should take it from, or whether the forecast alone is enough.

**Where I hesitated or was unsure:**
- I renamed the load from the default "Load" to "Household" without being asked. Easy to change.
- I chose Switchboard over the default Inverter based on how I understand the topology. I could not confirm HAEO's modelling rules.
- I did not check the Household load's entities after creation, so I have not verified the forecast values flow through.
- I did not add the current consumed power sensor, which was part of your request. That is the open item.
- I expanded and collapsed the Shedding section while looking for a current-power field. I left Allow shedding off and Consumption cost blank, and did not change either.

## add_policy_battery_wear run 1: passed


I set the Battery element's Discharge cost to 0.01 $/kWh and saved it. Reopening the dialog showed 0.01 still in place.

Points where I hesitated, was unsure, or may have made a mistake:

1. **"Wherever that energy goes" is unverified.** I chose the Battery's "Discharge cost" field because it is the only discharge-related price on the battery. I could not read any help text confirming that it applies to every discharge path (load, grid export, and so on). I assumed it does.
2. **Unit and value.** The field is labelled $/kWh, and I entered 0.01, which matches the $0.01 per kWh you asked for.
3. **Unexpected side effect.** After saving, a "Policies" element (1 device, 2 entities) appeared in the Home hub, and the entity count went from 60 to 63. I did not create it on purpose. I did not investigate why it appeared or whether it changes anything, so you may want to check it.
4. **Other battery settings left alone.** I did not change the Salvage value, Charge cost, Limit cost (100 $/kWh/h under Advanced), or Battery efficiency. The Limit cost is a different kind of setting, so I left it as it was.
5. **Screenshot check.** I used one screenshot to confirm the field and its unit, but I did not read any tooltip or docs for the field.

## add_policy_battery_wear run 2: passed


Every kWh discharged from the battery now costs $0.01. The battery's Discharge cost is set to 0.01 $/kWh, and HAEO created a policy named "Battery discharge cost" from it. That policy has source Battery and target Any, at 0.01 $/kWh, so the charge applies wherever the energy goes. I confirmed this in the policy's edit dialog and closed it without changes.

Where I hesitated or made mistakes:

- **Field choice:** I wasn't sure whether the battery's Discharge cost covers every destination or only some. I had no docs to check, so I added a Battery → Any policy by hand. HAEO rejected it as a duplicate, which showed the Discharge cost field already creates that rule. I did not add a second charge, so it isn't counted twice.
- **Leftover UI state:** I opened the Discharge cost entity picker and the Advanced section by accident, and I didn't review the Limit cost field (100 $/kWh/h), which I left unchanged. I also didn't check the Battery efficiency section.
- **Duplicate-rule check:** I saw the "Policy" element's Source/Target options and used them to try the policy route. This was a guess, and I didn't test whether the policy's Target "Any" matches all destinations, beyond what the form showed.
- **Unverified runtime effect:** I didn't check how the optimizer actually behaves with the new cost. The success messages and the policy's saved values are all I confirmed.

## add_policy_battery_wear run 3: passed


The battery now charges $0.01 per kWh discharged, applied to every destination. HAEO stores this as one policy, "Battery discharge cost" (source: Battery, target: Any, price 0.01 $/kWh), created from the battery's Discharge cost field. I confirmed the policy exists after the final save, but I did not reopen it to re-read the 0.01 price.

Where I hesitated or made mistakes:

- **Possible double charge:** After my first save, both the battery's Discharge cost (0.01) and an auto-created policy (0.01, Battery → Any) appeared. I worried this would charge 2 cents per kWh and cleared the battery field. That also deleted the policy, which showed the policy is generated from the field, not a separate charge.
- **Restored the field:** I set the battery's Discharge cost back to 0.01. The Policies list then showed one rule, so the end state is a single 1-cent charge. The interim clear-and-restore saves left the configuration unchanged in the end, but HAEO may have recomputed things during those saves.
- **Unverified semantics:** I can't read HAEO's code or docs. I assumed the discharge cost applies to all battery outflow, and the Target: Any policy suggests it does, but I did not test this with a plan.
- **Other fields left alone:** I did not touch Salvage value, Charge cost, the Limit cost of 100 $/kWh/h, or the efficiency settings, and did not check whether they interact with discharge cost.
- **Entity-count oddity:** The Policies entry on the hub still reads "2 entities" after the policy was briefly deleted and restored. I did not investigate why.

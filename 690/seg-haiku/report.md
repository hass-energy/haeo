# Benchmark runs

## add_battery_raw run 1: passed


I added the Sigenergy battery to HAEO. The new "Battery" device now appears on the Home hub with 21 entities.

I set these values on the Battery element:
- **Connection:** Inverter (the default). The battery sits behind the inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (currently 32.2 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (currently 12.8%).
- **Min charge level:** fixed 5%, so the battery is never discharged below 5%.
- **Max charge power:** Sigen Plant ESS Rated Charging Power (currently 16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (currently 19.2 kW).

I left the name as "Battery" and did not change the max charge level, the pricing, the efficiency, or the advanced sections.

I did not verify the saved values by reopening the battery configuration. The success dialog confirmed creation, and the entity count went from 41 to 66.

Points where I hesitated, were unsure, or made a mistake:
- **Mis-click:** My first click opened the Connection dialog by mistake because I had mislabelled the button. I closed it with Close and did not submit anything, so no connection was created.
- **Connection choice:** I kept the default "Inverter" connection. That assumes the battery is on the DC side of the inverter, which matches "connected through your inverter" but is an inference.
- **Min charge unit:** The 5% option offered as a fixed value was shown as "5 %". I chose that suggestion rather than typing a bare number, so I'm assuming it's the percentage the battery's min level expects.
- **Unexpected Policies device:** After submitting, a "Policies" device with 4 entities also appeared under HAEO. I did not create it, and I don't know whether HAEO adds it automatically or whether the battery triggered it. I did not investigate it further.
- **Battery name:** I left the default name "Battery" even though the hub already has other batteries from the same site could be confused with it. Naming it "Sigenergy Battery" might be clearer, but I didn't change it.

## add_battery_raw run 2: passed


I added the Sigenergy battery to the Home hub. HAEO created "Created configuration for Battery", and the Battery device now shows 21 entities.

Settings I entered:
- **Connection:** Inverter (the default, which matches a battery behind the inverter).
- **Capacity:** `sensor.sigen_plant_rated_energy_capacity` (32.24 kWh).
- **State of charge:** `sensor.sigen_plant_battery_state_of_charge`.
- **Min charge level:** fixed value 5 %.
- **Max charge power:** `sensor.sigen_plant_ess_rated_charging_power` (16.8 kW).
- **Max discharge power:** `sensor.sigen_plant_ess_rated_discharging_power` (19.2 kW).

I did not open the saved battery's settings afterwards to re-check these values.

Points where I hesitated or was unsure:
- **Connection:** The Sigenergy battery could be DC-coupled to the inverter, or it could be on a different connection. I kept the default "Inverter, DC" without confirming it against your hardware.
- **Battery name:** I left the default "Battery" rather than naming it after the Sigenergy unit.
- **Min charge level:** The field accepts a percentage or a sensor. I chose the fixed 5 % option, which showed the % unit in the dropdown.
- **Left at defaults:** Max charge level, the Battery efficiency section, the Advanced section, and the pricing fields (charge cost -0.001 $/kWh, discharge cost 0, salvage 0). You didn't mention these, and I did not review them.
- **Extra device:** After saving, a "Policies" device appeared with 4 entities. I did not create it on purpose and did not investigate whether it came from adding the battery.

## add_battery_raw run 3: passed


The Sigenergy battery is now added to the Home hub as "Battery", with 21 entities created under it.

**What I set:**
- **Connection:** Inverter (DC), the default. This fits a battery behind the Sigenergy inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.2 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8 %).
- **Min charge level:** fixed 5 %, so the battery is never discharged below 5 %.
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).

I confirmed these in a screenshot before submitting, and the success dialog said "Created configuration for Battery."

**Where I hesitated or may have gone wrong:**
- **Battery name:** I left the default "Battery" rather than something like "Sigenergy Battery". It's a cosmetic choice, but it's the name that will show up in HAEO.
- **Connection choice:** I accepted the default "Inverter, DC" without deliberately weighing it against "Switchboard". I chose it because you said the battery is connected through the inverter.
- **Max charge level:** I left it blank, since you only specified a lower limit. The battery can therefore charge up to full with HAEO's default behaviour.
- **Battery efficiency and Advanced sections:** I didn't open or change them, so they're at their defaults.
- **Salvage value and charge/discharge costs:** Also left at the defaults shown (salvage 0 $/kWh, charge cost -0.001 $/kWh, discharge cost 0 $/kWh). I didn't check whether those defaults suit your tariff.
- **Verification:** I checked the form before submitting, but I didn't open the new Battery device afterwards to confirm the saved values match.

## add_connection_ordered run 1: passed


I added the connection "Inverter to Switchboard transformer" to the Home hub. It runs from Inverter to Switchboard with two segments in this order:

1. **Efficiency: fixed 96%** (the transformer keeps 96% and loses 4%)
2. **Limit: fixed 8 kW** (the fuse cap on what reaches the switchboard)

The success dialog confirmed creation, and the hub list now shows the connection with 3 entities.

Points where I hesitated, were unsure, or could have gone wrong:

- **Segment order:** I put Efficiency before Limit so that the 8 kW cap applies to power after the 4% loss, which is what the fuse sees. I inferred that from the "applied in order" wording rather than from documentation, so I did not verify how the optimizer actually applies it.
- **Efficiency units:** The field offered "Fixed value 96 %" when I typed 96, and I picked that rather than 0.96. The UI displayed it as a percentage, so I believe it is right, but I did not check the stored value.
- **Limit meaning:** I assumed the 8 kW limit caps instantaneous power through the connection. I did not confirm that it is not an energy or per-interval limit.
- **Connection name:** The default was "Connection". I renamed it to "Inverter to Switchboard transformer" for clarity. That was my choice, not something you asked for.
- **Direction:** The help text says the connection is one-way. I left the default direction, so power can flow only from Inverter to Switchboard, which matches your setup.
- **Not re-checked:** I did not reopen the saved connection to confirm the segments and values persisted as entered.

## add_connection_ordered run 2: passed


I added a connection named "Transformer" from Inverter to Switchboard in the Home hub. HAEO confirmed "Created configuration for Transformer", and it now appears under Home with 3 entities.

The connection has two segments, applied in this order:
1. **Efficiency: fixed value 96 %**. This models the 4% transformer loss.
2. **Limit: fixed value 8 kW**. This is the switchboard fuse.

I put Efficiency first so the 8 kW cap applies to power that actually reaches the switchboard, after the loss. Putting the limit first would have capped the inverter side and cut the usable output to about 7.68 kW.

Points where I hesitated or was unsure:
- **Efficiency units:** The field showed no unit, so I entered 96 and it displayed as "96 %". I assumed percent rather than a 0–1 fraction. The option listing confirmed "Fixed value 96 %".
- **Segment order:** The dialog lets you order segments, and I was not sure whether HAEO applies them source-to-target. I went with the order that matches physics. I did not check the result in the saved configuration.
- **Connection name:** The user did not specify one, so I named it "Transformer" rather than keeping the default "Connection".
- **Limit field:** The Limit dropdown also offered many sensors. I chose the fixed 8 kW value, not a sensor, because the fuse rating is a constant.
- **Verification:** I checked only that the connection was created and listed. I did not reopen it to confirm the saved segments and values.

## add_connection_ordered run 3: passed


I added the connection "Inverter to Switchboard" to the Home hub. HAEO confirmed "Created configuration for Inverter to Switchboard", and the hub now lists it with 3 entities.

The connection goes from Inverter (source) to Switchboard (target) with two segments, in this order:
1. **Efficiency**, fixed at 96%, for the 4% transformer loss.
2. **Limit**, fixed at 8 kW, for the switchboard fuse.

I put the limit after the efficiency so the 8 kW cap applies to power arriving at the switchboard, not power leaving the inverter.

Points where I hesitated or was unsure:
- **Efficiency units:** The field offered "Fixed value 96 %" and I picked that option rather than entering 0.96. I did not check how HAEO stores the value.
- **Limit units:** The picker offered "Fixed value 8 kW", so I used that. I did not confirm the saved value by reopening the connection.
- **Segment order:** The brief didn't specify an order. I chose efficiency first then limit, which is my reading of "no more than 8 kW arrives at the switchboard."
- **Connection name:** The brief didn't name it. I renamed the default "Connection" to "Inverter to Switchboard".
- **Direction:** The connection is one-way, as HAEO's help text describes. I did not add a reverse connection, since the brief asked only for the inverter-to-switchboard path.
- **Verification:** I confirmed the success message and the new entry in the hub list, but did not reopen the connection to check every saved field.

## add_connection_raw run 1: passed


The connection is set up: Inverter to Switchboard with a fixed 10 kW limit. HAEO now lists a new "Inverter to Switchboard" connection under Home, with 2 entities.

I did not reopen the saved connection to read the limit back. The limit was confirmed as "Fixed value 10 kW" in the form before I submitted, and the success message appeared.

Points where I hesitated or made a choice:
- **Wrong dialog first:** I clicked the hub's "Configure" button by mistake, which opened the Home hub settings. I closed it without changing anything and used the "Connection" add button instead.
- **Name:** You didn't ask for a name, so I renamed the default "Connection" to "Inverter to Switchboard" so it is easy to identify. It can be changed if you prefer another name.
- **Units:** The limit field took a bare "10" and offered it as "Fixed value 10 kW". I accepted that option rather than entering a unit myself.
- **Direction:** The connection is one-way, which matches the cable limit you described (inverter to switchboard). The form says power in the other direction needs a second connection with the endpoints swapped. I did not add one, because you only asked for this direction.

## add_connection_raw run 2: passed


I added the connection. HAEO confirmed "Created configuration for Inverter to Switchboard", and the Home hub now lists an "Inverter to Switchboard" Connection device with 2 entities.

- **Source and target:** Inverter as the source and Switchboard as the target, which were already selected when the form opened.
- **Limit:** one Limit segment set to a fixed value of 10 kW, chosen from the "Fixed value 10 kW" suggestion. The form's Limit field takes entities or values, and the 10 kW suggestion was the only fixed value offered.
- **Name:** I renamed the connection from the default "Connection" to "Inverter to Switchboard". You didn't ask for a name, so change it if you prefer another.

Points where I hesitated or was unsure:
- I did not check the 10 kW limit against the live Connection entity's attributes afterwards, so I'm relying on the form and the success message to confirm the value.
- The connection is one-way, as the form's help text says. Power flowing back from the Switchboard to the Inverter is not limited by this connection. The help text suggests adding a second connection with the endpoints swapped if you need that, and I did not add one.
- I assumed the Limit field's units are kW because the dropdown labelled the value "10 kW". I did not confirm the unit independently.

## add_connection_raw run 3: passed


I added the connection from the Inverter to the Switchboard with a 10 kW limit. The Home hub now lists "Inverter to Switchboard" as a Connection device with 2 entities.

Configuration:
- **Source:** Inverter (the default).
- **Target:** Switchboard (the default).
- **Segment:** one Limit, set to a fixed value of 10 kW. The picker shows it as "Fixed value 10 kW".
- **Name:** "Inverter to Switchboard" instead of the default "Connection".

I did not reopen the connection to check its saved settings. The success is confirmed only by the new device and entity counts on the hub.

Points where I hesitated or was unsure:
- **Units:** The Limit field gave no unit label. I entered 10 because the sensors in the picker are shown in kW, and the picker then read "10 kW". I did not confirm this against HAEO's documentation.
- **Direction:** The connection is one-way, as the dialog says. Power flowing back from the Switchboard to the Inverter would need a second connection with the endpoints swapped. You only asked for the inverter-to-switchboard cable, so I did not add one.
- **Name:** You did not give a name, so I chose "Inverter to Switchboard". Easy to change if you prefer another.
- **Limit type:** I picked the "Limit" segment rather than "Price" or "Efficiency", since the cable rating is a power limit.
- **Mistake:** I pressed Escape once while the Limit picker was open. It only closed the picker and did not discard the form, but I could have been more careful.

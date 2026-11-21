# Benchmark runs

## add_buffer_reserve run 1: passed


I added a Buffer to your Home setup so HAEO keeps enough energy in the battery to cover a 12-hour power cut. HAEO showed "Created configuration for Buffer", and the new Buffer is listed under Home. I didn't check that the optimizer now holds a reserve in practice.

- **Kind:** Reserve (keep energy).
- **Load:** your Load.
- **Generation:** Solar, so it counts toward covering the outage.
- **Battery:** your Battery.
- **Window:** 12 hours. The form already had this as its default and I left it.

Points where I hesitated or left things to defaults:
- **Level:** I left it empty. It is optional and I couldn't tell what an empty value means. I assumed it means "cover the full window", but I didn't confirm that. The only suggestion offered was the battery state-of-charge sensor, which didn't seem right for this.
- **Shortfall cost:** I left it at the default of 0.05 $/kWh/h. I don't know whether that is high enough to make HAEO reliably hold the reserve, and I didn't change it.
- **Switchboard and Grid:** I didn't add them as participants. The form only offered Load, Solar and Battery, and those seemed to be the right ones.

## add_buffer_reserve run 2: passed


I added a Buffer to the Home hub, set as a Reserve with a 12 h window. Its participants are Load, Solar as generation, and Battery as the battery. HAEO showed "Created configuration for Buffer", and a Buffer device with 6 entities now appears under Home. I haven't checked whether the optimizer now holds the extra charge.

Points where I hesitated:
- **Level:** I left it blank and didn't check what HAEO treats blank as. I assumed it means a full 12-hour reserve, but it may not.
- **Window:** The form already had 12 h filled in as a fixed value, which matches your 12 hours, so I left it.
- **Shortfall cost:** I left the default of 0.05 $/kWh/h without knowing if that is a sensible penalty for running short.
- **Grid and Inverter:** I left them out of the participants because the form only asks for loads, generation and batteries. I assumed that is right for an outage, but I'm not certain.

## add_buffer_reserve run 3: passed


I added a Buffer to your Home hub, set to Reserve with a 12 h window. The Buffer now shows as a new device under Home with 6 entities. I haven't checked that the reserve actually holds enough energy for a 12-hour outage.

- **Loads:** Load.
- **Generation:** Solar, so it counts as still producing during a power cut.
- **Batteries:** Battery.
- **Window:** 12 h, which was already filled in by default.
- **Shortfall cost:** left at the default 0.05 $/kWh/h.
- **Level:** left blank.

Where I hesitated or was unsure:
- I wasn't sure what the optional "Level" field does. It looked like a percentage setting, and the task didn't mention one, so I left it empty. I don't know whether blank means "cover the full 12 hours of load".
- The 12 h window and the 0.05 shortfall cost were pre-filled. I kept them without testing whether 0.05 is high enough to make HAEO hold the reserve firmly.
- I didn't add Grid or Inverter as participants. The form only offered Loads, Generation and Batteries, and I assumed those were all that mattered for an outage.

## add_policy_battery_wear run 1: passed


I added a Policy rule called "Battery wear". It charges $0.01 per kWh on any energy leaving the Battery. Home Assistant showed "Created configuration for Policies." and I clicked Finish. I didn't reopen the Policy to check it afterwards.

- **From:** Battery.
- **To:** left as Any, so the charge applies wherever the discharged energy goes.
- **Price:** a fixed value of 0.01 $/kWh.

Points where I hesitated or made a mistake:
- **Extra Grid element:** The element dropdown was a plain select, so I used the keyboard to pick Battery. That added Grid and Battery together. I removed Grid before submitting.
- **"Any" on the To side:** The To list offered Grid, Battery and Load but not Inverter or Solar. I assumed "Any" covers every destination, as the help text says, but I couldn't check that.
- **Price entry:** Typing 0.01 did nothing until I selected the "Fixed value 0.01 $/kWh" suggestion that appeared.

## add_policy_battery_wear run 2: passed


HAEO now has a Policy with one rule, "Battery wear". The rule charges a fixed $0.01/kWh on energy flowing from Battery to Any, so it applies wherever the discharged energy goes. The dialog said "Created configuration for Policies." I didn't reopen the Policy afterwards to check that the rule saved as entered.

Points where I hesitated or made mistakes:
- **Element picker:** The "From" picker is a plain dropdown, and typing into it failed. I picked items with the keyboard and twice added the wrong element (Solar, then Grid). I removed each one and re-added Battery. The form showed only Battery in "From" when I submitted.
- **"To" side:** I left it as "Any" so the charge covers every destination. I wasn't sure whether "Any" includes the Switchboard, Inverter and similar parts.
- **Price units:** I assumed the price field means $/kWh. The "Fixed value 0.01 $/kWh" option confirmed it.
- **Rule name:** The form asked for no policy name, so I renamed the default "Rule 1" to "Battery wear".

## add_policy_battery_wear run 3: passed


I added a Policy to HAEO with one rule, "Battery wear". It charges a fixed 0.01 $/kWh on power flowing from the Battery to anywhere. HAEO showed "Created configuration for Policies", and I clicked Finish. I didn't reopen the Policy afterwards to confirm the saved rule.

I left "To" empty, which the dialog says means the rule applies to every element on that side.

Points where I hesitated or slipped:
- **Element picker:** the "From" picker is a native dropdown. My first attempt to type into it failed, so I selected Battery with the keyboard instead. Battery then showed as a chip under "From".
- **Price entry:** typing 0.01 only offered a "Fixed value 0.01 $/kWh" suggestion, so I clicked it to confirm. I assumed $/kWh was the right unit for "1 cent per kWh".
- **Rule name:** the dialog suggested "Rule 1". I renamed it to "Battery wear" so it's recognisable later.

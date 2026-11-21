# Benchmark runs

## add_policy_battery_wear run 1: passed


I added a policy called "Battery wear" to the Home hub. It treats every kWh leaving the Battery as costing $0.01, whatever the destination. The setup showed a success message, and a new "Policies" device now appears in the hub. I didn't open the policy again to check the saved values.

The policy is enabled, with the source set to Battery, the target left on "Any" and the price set to a fixed 0.01 $/kWh.

Points where I was unsure:
- **Direction of the rule:** I assumed a policy price applies to energy flowing from the source to the target, so "source = Battery, target = Any" means every discharge. The form doesn't say this. I couldn't confirm it.
- **Battery to Battery:** "Any" as target might include a battery-to-battery flow, which is harmless here.
- **Policy name:** I made up "Battery wear", since nothing specified one.

## add_policy_battery_wear run 2: passed


I added a policy called "Battery wear" to the Home hub. It treats every kWh discharged from the battery as costing $0.01. Home Assistant reported "Created configuration for Policies", and a new "Policies" device now shows on the integration page.

The policy is enabled, with Battery as the source, the target left on its default of Any, and a fixed price of 0.01 $/kWh. I didn't open the policy again afterwards to check the saved values, and I haven't seen it affect the optimizer's plan.

Points where I hesitated or was unsure:
- **Target setting:** I never clicked the Target "Any" button. The form didn't clearly show which option was selected, so I assumed Any was the default. If it wasn't, the policy may not apply to every destination.
- **Price unit:** the price field offered "0.01 $/kWh", so I took that to be the right unit for 1 cent per kWh.
- **Policy name:** I chose "Battery wear" myself, since you didn't give one.

## add_policy_battery_wear run 3: passed


I added a Policy to your Home hub called "Battery wear". It's enabled, with the source set to Battery, the target set to Any, and a price of 0.01 $/kWh. That means every kWh leaving the battery should cost 1 cent, whatever it goes to.

HAEO showed a "Created configuration for Policies" message, and a new "Policies" device with 2 entities now appears under Home. I didn't open the policy again to check the saved values.

Points where I hesitated or was unsure:
- **Target:** I chose "Any" rather than listing elements, because you said "wherever that energy goes". I couldn't tell whether "Any" also counts battery energy going to the Switchboard or Inverter. I assumed it does.
- **Price field:** It accepted a typed number only after I picked the "Fixed value 0.01 $/kWh" option from the dropdown. I assumed that option was correct.
- **Policy name:** You didn't give one, so "Battery wear" is my choice.
- **Progress note:** I went quiet for a few steps before telling you what I was doing.

## edit_battery_min_charge run 1: passed


The battery's minimum charge level is now 20% instead of 5%. HAEO showed "Configuration updated successfully". I reopened the Battery settings afterwards and they showed 20%. I've already marked the task as done.

Points where I hesitated or slipped:
- **Editing the value:** I wasn't sure how to change the field. I removed the old 5% chip, typed 20, and picked the "Fixed value 20 %" option from the list. The field is a combined sensor-or-value picker, so I couldn't just overwrite the number.
- **Opening the settings:** I assumed the "Battery" button on the hub page was the configure button. It was.

## edit_battery_min_charge run 2: passed


I raised the Battery's minimum charge level from 5% to 20%. HAEO showed "Configuration updated successfully". When I reopened the Battery settings, Min charge level showed 20 %. I left the other settings as they were.

Points where I hesitated or slipped:
- I wasn't sure which control opened the Battery settings. I clicked the "Battery" button and it opened the configuration dialog, so that worked.
- After removing the 5% chip, HAEO suggested the battery state-of-charge sensor in the dropdown. I ignored it and typed 20 as a fixed value, then picked "Fixed value 20 %".
- I pressed Escape to close the dialog after checking. I didn't confirm that it closed cleanly.

## edit_battery_min_charge run 3: passed


The battery's minimum charge level is now 20%, up from 5%. HAEO showed "Configuration updated successfully" after I submitted. I reopened the Battery configuration and it showed "Fixed value 20 %" for Min charge level.

Points where I hesitated or was unsure:
- **Opening the editor:** I guessed that the "Battery" button under the Home hub was the one that opens the settings. It was correct.
- **Editing the value:** The 5% value appeared as a chip rather than a text box. I wasn't sure it was editable, so I clicked it to turn it into a field. I then typed 20 and pressed Enter to confirm it before submitting.
- **Closing the check dialog:** I left the verification dialog open without submitting again.

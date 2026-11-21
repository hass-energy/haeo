# Benchmark runs

## add_buffer_reserve run 1: passed


I added an "Outage reserve" buffer to HAEO. It is set up as a 12-hour reserve, but I'm not sure it will hold enough energy yet.

**What I set:**
- **Name:** Outage reserve
- **Kind:** Reserve (keep energy), not Headroom
- **Participants:**
  - Loads: Load (your house)
  - Generation: Solar, since it keeps producing during a cut
  - Batteries: Battery
- **Window:** 12 h (the default, which matches your requirement)
- **Shortfall cost:** 0.05 $/kWh/h (the default; I didn't change it)
- **Level:** left empty

HAEO confirmed "Created configuration for Outage reserve," and the Home hub now lists the buffer with 6 entities.

**Where I hesitated or may have gone wrong:**
- **Level left empty.** The only option offered was the battery state-of-charge sensor, which is a percentage and not an energy amount, so I didn't use it. I don't know your house's energy use over 12 hours, so I couldn't enter a fixed kWh reserve. If HAEO doesn't derive the reserve from the load forecast when Level is empty, the buffer may not hold enough. You may want to set Level to a kWh value.
- **Preview looked odd.** The "What it would do" preview said loads over the window take up to 24% of battery charge, and that the battery goes as low as 5% with the buffer, the same as the plan now. I didn't understand why the buffer changed nothing, and I didn't check the result after saving.
- **Accidental collapse.** I clicked the Requirement heading to close a dropdown and collapsed that section. I reopened it and confirmed the 12 h window was still set before submitting.
- **Solar and the 12-hour window.** I included Solar because you said it helps during an outage. I didn't check whether HAEO counts it as reliable backup or how much it contributes. The 12-hour window and Solar's share are the parts I'd most want to verify.

## add_buffer_reserve run 2: passed


I added a HAEO Buffer called "Power cut reserve" to keep battery energy for a 12-hour outage. It saved, and reopening it showed the values below. The 24% reserve level is a rough figure, though, and I think you should check it.

**What I set:**
- **Kind:** Reserve (keep energy), not Headroom.
- **Loads:** Load.
- **Generation:** Solar. Solar keeps producing during an outage, so it counts toward the reserve.
- **Batteries:** Battery.
- **Window:** 12 h (already filled in as the default).
- **Level:** 24% (fixed value).
- **Shortfall cost:** left at the default of 0.05 $/kWh/h.

**Where I hesitated or was unsure:**
- **The 24% level is a guess.** I don't know your household's consumption, and no load-energy sensor was offered. The only option in the Level picker was the battery state-of-charge sensor. I used 24% because HAEO's preview said that covering the loads over the 12-hour window takes up to 24% of battery charge. Please check this against your real usage.
- **The preview changed after I entered 24%.** It went from "up to 24%" to "up to 43%" once the Level was set and I renamed the buffer. I didn't work out why. The chart also said that with the buffer the battery goes as low as 5%, which doesn't clearly show the reserve being held. I submitted anyway.
- **I didn't confirm the Level unit.** The picker showed "%" once I entered 24, so I treated it as a percentage of battery charge, not an energy amount.
- **I renamed the buffer** from the default "Buffer" to "Power cut reserve" so it's easy to find. That's cosmetic only.
- **Solar may make the reserve too conservative.** I counted solar as generation that keeps producing. The 24% figure may not account for it, so the reserve could be higher than needed.
- **Small slip:** my first attempt to open the Level picker timed out because the Battery picker was still open. I closed it and retried, and nothing was lost.

## add_buffer_reserve run 3: passed


I added an "Outage reserve" buffer to the Home hub. The buffer now appears in the hub's device list with 7 entities, and the success dialog confirmed it was created.

What I set up:
- **Kind:** Reserve (keep energy), the default.
- **Participants:** Load as the loads to keep running, Solar as the generation that keeps producing during the outage, and Battery as the batteries that hold the reserve.
- **Window:** 12 h, the default, which matches your longest outage.
- **Level:** Fixed 43%.
- **Shortfall cost:** 0.05 $/kWh/h, the default. I left it alone.

I did not check the entities HAEO created or run an optimisation, so the result is not verified beyond the success message.

Points where I hesitated or was unsure:
- **Level value:** The "What it would do" preview said covering the loads over 12 h takes "up to 24%" of battery charge, and later "up to 43%". The figure changed while I was editing and I could not tell why. I chose 43% because a reserve that is too low fails the outage, while one that is too high only costs some battery use. I have not confirmed whether the preview already nets off solar. If it does not, 43% is more than you need, and the figure could be lowered.
- **Level as a fixed number:** The Level field also accepts a sensor. I chose a fixed value because I could not find a sensor for the required reserve. A fixed value will not adjust if your house load changes.
- **Solar as a participant:** I included Solar because you said it keeps producing during an outage. I could not confirm how HAEO credits that solar in the reserve calculation.
- **Shortfall cost:** It is required, and I kept the default 0.05 $/kWh/h. I do not know how strongly that default pushes the optimiser to keep the reserve, so you may want to review it.
- **Battery participant:** The Battery option is one of the batteries that holds the buffer. My Sigen battery is the only battery HAEO shows, so I added it without checking whether there is more than one.
- **Buffer name:** I renamed it "Outage reserve" from the default "Buffer". That is my own choice and easy to change.

## add_buffer_reserve run 4: passed


I added an "Outage reserve" buffer to the Home hub. It is a reserve over a 12-hour window, covering Load, Solar and Battery, with the level set to 50% of battery charge. The success dialog confirmed it was created, and it now appears under Home with 7 entities.

**Points where I hesitated, was unsure, or may have made a mistake:**

- **Level value (50%) is a judgement call.** The preview said covering the loads over 12 hours takes up to 49% of battery charge, so I chose 50%. I did not check your actual load power, and I did not confirm how much solar would offset this, so the figure may be too high or too low.
- **The preview changed unexpectedly.** It first said 24%, then 49% after I renamed the buffer. I don't know why. It also still said "as low as 5%" after I set the level, so I could not confirm the preview reflected my level.
- **Level units.** The field accepts a percentage, and the picker offered the battery state-of-charge sensor. I entered a fixed percentage rather than the sensor, and I did not check whether HAEO reads it as battery charge or as energy.
- **Cost of the reserve.** The battery is currently at about 12.8% charge, so a 50% reserve means HAEO will need to charge the battery, possibly from the grid. I left the default shortfall cost of 0.05 $/kWh/h without deciding whether it suits you.
- **Participant choices.** I added Load, Solar and Battery, and I did not add Grid or Inverter. I believe solar should count because it keeps producing during an outage, but I could not verify how HAEO treats it.
- **Window and kind.** I kept the default 12-hour window and "Reserve" kind, which match your requirement. I did not change the default name until I renamed it to "Outage reserve".
- **Result not checked.** I did not look at the buffer's saved configuration or its resulting plan after creation, so I have not confirmed the 12-hour reserve is working as intended.

## add_buffer_reserve run 5: passed


I created a HAEO buffer called "Outage reserve" to keep enough battery charge for a 12-hour outage, but I did not set an explicit energy amount, and I could not confirm the reserve is actually holding charge.

**What I set up:**
- **Kind:** Reserve (keep energy), not Headroom.
- **Window:** 12 h, the default, which matches your outage length.
- **Participants:** Load (the house loads), Solar (generation that keeps producing during an outage), and Battery (the store holding the reserve).
- **Level:** left empty. HAEO's preview computes the energy needed to cover the loads over the window.
- **Shortfall cost:** left at the default of 0.05 $/kWh/h.

The success dialog confirmed the buffer was created, and it now appears in the hub's device list.

**Where I hesitated or may have gone wrong:**
- **Level left empty.** The field is not marked required, and the preview said covering the loads over 12 h takes up to 24% of battery charge. But the same preview said the battery would drop "as low as 5%" with the buffer, the same as the current plan. That suggests the reserve may not raise the floor, and an empty Level may mean no reserve at all. I did not check this further. Confirm the buffer's effect before relying on it during an outage.
- **Level search found no load sensor.** Searching "load" in the Level picker returned nothing, and the only suggestion was the battery state-of-charge sensor. I did not know which unit Level expects (kWh or %), so I did not type a number.
- **Solar as a participant.** I included Solar because you said it helps during a power cut. HAEO's text says generation "keeps producing through an outage" counts toward the reserve, but I could not check how much solar it credits.
- **Name.** I renamed the buffer "Outage reserve" without being asked; the default was "Buffer".
- **Battery state.** The battery sensor showed about 12.8% state of charge when I opened the picker. That is low for a 12-hour outage, and I did not check whether the reserve is achievable from that level.

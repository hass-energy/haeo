# Transcript

```
$ ./browse look
```

```
Page: /config/integrations/integration/haeo
- generic [ref=f2e4]:
  - complementary [ref=f2e5]:
    - generic [ref=f2e7]:
      - generic [ref=f2e8]:
        - generic "Sidebar toggle" [ref=f2e10]:
          - button "Sidebar toggle" [ref=f2e11] [cursor=pointer]
        - generic [ref=f2e14]: Home Assistant
      - generic [ref=f2e15]:
        - generic [ref=f2e17]:
          - generic:
            - listitem [ref=f2e19] [cursor=pointer]:
... (324 more lines in actions.jsonl)
```

```
$ ./browse click f2e117
```

```
Clicked f2e117.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (107 more lines in actions.jsonl)
```

Connection Inverter is default and correct. Fill capacity.

```
$ ./browse type f2e501 rated energy capacity
```

```
Typed into f2e501.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (116 more lines in actions.jsonl)
```

```
$ ./browse click f2e626 >/dev/null; ./browse type f2e507 state of charge | grep -A12 'listbox'
```

```
                  - listbox [ref=f2e650]:
                    - group [ref=f2e651]:
                      - option "Current value 12.8 % Sigen Plant Battery State of Charge sensor.sigen_plant_battery_state_of_charge" [ref=f2e652] [cursor=pointer]:
                        - img "Current value 12.8 %" [ref=f2e653]:
                          - generic [ref=f2e654]: "12.8"
                          - generic [ref=f2e655]: "%"
                        - generic [ref=f2e656]:
                          - generic [ref=f2e657]: Sigen Plant Battery State of Charge
                          - generic [ref=f2e658]: sensor.sigen_plant_battery_state_of_charge
          - generic [ref=f2e509]:
            - button [expanded] [ref=f2e511] [cursor=pointer]:
              - heading "Limits" [level=3] [ref=f2e512]
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e652 >/dev/null; ./browse type f2e545 charging power | grep -A12 'listbox'
```

```
                  - listbox [ref=f2e668]:
                    - group [ref=f2e669]:
                      - option "Add all 2" [ref=f2e670] [cursor=pointer]
                      - option "Current value 16.8 kW Sigen Plant ESS Rated Charging Power sensor.sigen_plant_ess_rated_charging_power" [ref=f2e675] [cursor=pointer]:
                        - img "Current value 16.8 kW" [ref=f2e676]:
                          - generic [ref=f2e677]: "16.8"
                          - generic [ref=f2e678]: kW
                        - generic [ref=f2e679]:
                          - generic [ref=f2e680]: Sigen Plant ESS Rated Charging Power
                          - generic [ref=f2e681]: sensor.sigen_plant_ess_rated_charging_power
                      - option "Current value 19.2 kW Sigen Plant ESS Rated Discharging Power sensor.sigen_plant_ess_rated_discharging_power" [ref=f2e682] [cursor=pointer]:
                        - img "Current value 19.2 kW" [ref=f2e683]:
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e675 >/dev/null; ./browse type f2e551 discharging power | grep -A12 'listbox'
```

```
                  - listbox [ref=f2e706]:
                    - group [ref=f2e707]:
                      - option "Current value 19.2 kW Sigen Plant ESS Rated Discharging Power sensor.sigen_plant_ess_rated_discharging_power" [ref=f2e708] [cursor=pointer]:
                        - img "Current value 19.2 kW" [ref=f2e709]:
                          - generic [ref=f2e710]: "19.2"
                          - generic [ref=f2e711]: kW
                        - generic [ref=f2e712]:
                          - generic [ref=f2e713]: Sigen Plant ESS Rated Discharging Power
                          - generic [ref=f2e714]: sensor.sigen_plant_ess_rated_discharging_power
          - generic [ref=f2e553]:
            - button [expanded] [ref=f2e555] [cursor=pointer]:
              - heading "Pricing" [level=3] [ref=f2e556]
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e708 >/dev/null; ./browse type f2e523 5 | grep -B2 -A12 'listbox'
```

```
                  - generic [ref=f2e521]: Min charge level
                  - 'combobox "Min charge level: search entities or enter a value" [expanded] [ref=f2e523]': "5"
                  - listbox [ref=f2e732]:
                    - group [ref=f2e733]:
                      - option "Fixed value 5 %" [ref=f2e734] [cursor=pointer]:
                        - generic [aria-hidden] [ref=f2e735]:
                          - generic [ref=f2e736]: "5"
                          - generic [ref=f2e737]: "%"
                        - generic [ref=f2e738]: Fixed value
                - generic [ref=f2e526]:
                  - generic [ref=f2e527]: Max charge level
                  - 'combobox "Max charge level: search entities or enter a value" [ref=f2e529]'
... (3 more lines in actions.jsonl)
```

```
$ ./browse click f2e734 | grep -E 'combobox|Fixed value|textbox' | head -20
```

```
            - textbox "Battery name*" [ref=f2e460]:
                    - 'combobox "Capacity: search entities or enter a value" [ref=f2e501]'
                    - 'combobox "State of charge: search entities or enter a value" [ref=f2e507]'
                      - button "Fixed value 5 %" [ref=f2e741] [cursor=pointer]:
                        - generic [ref=f2e745]: Fixed value
                    - 'combobox "Min charge level: search entities or enter a value" [ref=f2e523]'
                  - 'combobox "Max charge level: search entities or enter a value" [ref=f2e529]'
                    - 'combobox "Max charge power: search entities or enter a value" [ref=f2e545]'
                    - 'combobox "Max discharge power: search entities or enter a value" [ref=f2e551]'
                      - button "Fixed value 0 $/kWh" [ref=f2e568] [cursor=pointer]:
                        - generic [ref=f2e572]: Fixed value
                    - 'combobox "Salvage value: search entities or enter a value" [ref=f2e576]'
... (6 more lines in actions.jsonl)
```


I've filled in the battery form. Next I'll check that every field kept its value, then submit.

```
$ ./browse look | grep -E 'Current value|Fixed value [0-9]|Sigen|Submit'
```

```
                        - img "Current value 32.24 kWh" [ref=f2e635]:
                        - generic [ref=f2e638]: Sigen Plant Rated Energy Capacity
                      - button "Remove Sigen Plant Rated Energy Capacity" [ref=f2e639] [cursor=pointer]
                        - img "Current value 12.8 %" [ref=f2e661]:
                        - generic [ref=f2e664]: Sigen Plant Battery State of Charge
                      - button "Remove Sigen Plant Battery State of Charge" [ref=f2e665] [cursor=pointer]
                      - button "Fixed value 5 %" [ref=f2e741] [cursor=pointer]:
                        - img "Current value 16.8 kW" [ref=f2e691]:
                        - generic [ref=f2e694]: Sigen Plant ESS Rated Charging Power
                      - button "Remove Sigen Plant ESS Rated Charging Power" [ref=f2e695] [cursor=pointer]
                        - img "Current value 19.2 kW" [ref=f2e717]:
                        - generic [ref=f2e720]: Sigen Plant ESS Rated Discharging Power
... (4 more lines in actions.jsonl)
```

```
$ ./browse click f2e621 | head -40
```

```
Clicked f2e621.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e749]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Success" [ref=f2e750]
    - generic [ref=f2e751]:
      - paragraph [ref=f2e753]: Created configuration for Battery.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e756 >/dev/null; ./browse done "Added Battery to Home, connected to Inverter, with capacity, SoC, rated charge/discharge power sensors, and min charge level fixed 5%."
```

```
Recorded. You can stop now.
```

I added a battery named "Battery" to the Home hub and connected it to the Inverter. HAEO showed "Created configuration for Battery." I didn't reopen the new battery afterwards to check its saved values.

- **Capacity:** the Sigen Plant Rated Energy Capacity sensor (currently 32.24 kWh).
- **State of charge:** the Sigen Plant Battery State of Charge sensor (currently 12.8%).
- **Max charge power:** the Sigen Plant ESS Rated Charging Power sensor (16.8 kW).
- **Max discharge power:** the Sigen Plant ESS Rated Discharging Power sensor (19.2 kW).
- **Min charge level:** a fixed 5%, so the battery is never discharged below that.

I left the other settings at their defaults: max charge level, pricing (salvage value, charge cost, discharge cost), battery efficiency and the advanced options.

Points where I hesitated or went beyond the task:
- **Connection:** the form offered Inverter or Switchboard. I kept the Inverter, which was already selected, because you said the battery connects through your inverter.
- **Min charge level:** I typed 5 into the search box and picked the "Fixed value 5 %" option, because I wasn't sure a typed number would count as a value. It did.
- **Pricing defaults:** the charge cost default is -0.001 $/kWh, which looked odd. I didn't change it.
- **Final check:** I confirmed the chosen sensors were still shown just before submitting.


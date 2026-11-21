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
... (312 more lines in actions.jsonl)
```

```
$ ./browse click f2e114
```

```
Clicked f2e114.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (39 more lines in actions.jsonl)
```

Inverter is selected (DC), correct. Open forecast picker.

```
$ ./browse click f2e485
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (242 more lines in actions.jsonl)
```


```
$ ./browse type f2e485 energy_production | head -30
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (18 more lines in actions.jsonl)
```

```
$ ./browse look | grep -n -E "Add all|option" | head -8
```

```
49:                    - option "Add all 32" [ref=f2e799] [cursor=pointer]
50:                    - option "Forecast East solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_east" [ref=f2e504] [cursor=pointer]:
55:                    - option "Forecast East solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_east" [ref=f2e512] [cursor=pointer]:
60:                    - option "Forecast East solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_east" [ref=f2e520] [cursor=pointer]:
65:                    - option "Forecast East solar production forecast Estimated energy production - 6 days from now sensor.energy_production_d6_east" [ref=f2e528] [cursor=pointer]:
70:                    - option "Forecast East solar production forecast Estimated energy production - 7 days from now sensor.energy_production_d7_east" [ref=f2e536] [cursor=pointer]:
75:                    - option "Forecast East solar production forecast Estimated energy production - day after tomorrow sensor.energy_production_d2_east" [ref=f2e544] [cursor=pointer]:
80:                    - option "Forecast East solar production forecast Estimated energy production - today sensor.energy_production_today_east" [ref=f2e552] [cursor=pointer]:
```

32 = 8×4, exactly the Forecast.Solar sensors.

```
$ ./browse click f2e799 | grep -v -E "^\s+- (generic|img|option)" | head -60
```

```
Clicked f2e799.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
    - banner [ref=f2e419]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - paragraph [ref=f2e436]: Configure solar forecasting and parameters
            - textbox "Solar name*" [ref=f2e443]:
              - /placeholder: ""
              - text: Solar
            - radiogroup "Connection *" [ref=f2e448]:
              - radio "Inverter, DC" [checked] [ref=f2e449] [cursor=pointer]:
... (45 more lines in actions.jsonl)
```

```
$ ./browse click f2e494 | head -40
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1125]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1126]
    - generic [ref=f2e1127]:
      - paragraph [ref=f2e1129]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e1132 | grep -i solar | head
```

```
          - button "Solar" [ref=f2e114] [cursor=pointer]
                          - generic: Solar
                      - generic: Solar
                      - generic: Solar
                        - generic "Solar" [ref=f2e1137]:
                          - button "Solar" [ref=f2e1138] [cursor=pointer]
                      - generic: Solar
```

```
$ ./browse done "Added Solar to Home, connected to Inverter (DC), with all 32 Forecast.Solar energy production sensors (east/north/south/west x 8 days each). Solar now appears in the hub."
```

```
Recorded. You can stop now.
```

I added Solar to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar estimated energy production sensors. That's 8 for each of east, north, south and west: today, tomorrow, the day after, and 3 to 7 days from now. The form showed a success message, and Solar now appears in the hub's device list. I didn't open the new Solar entry to check its saved settings.

Points where I hesitated or could have gone wrong:
- **Add all button:** the picker's "Add all" first offered 38 sensors. That count included unrelated Sigen Plant sensors, such as PV Power and Consumed Power. I typed "energy_production" into the search first, which cut the list to 32, then used "Add all".
- **Connection:** I left the default, "Inverter, DC". You said the panels feed into your inverter, so I believed that was right. I didn't compare it with the Switchboard (AC) option beyond that.
- **Name:** I kept the default name "Solar" without changing it.


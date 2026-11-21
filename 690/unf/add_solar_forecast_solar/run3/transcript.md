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

Inverter connection is selected already. Open the forecast picker.

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

32 = 4 directions × 8 days. Add all.

```
$ ./browse click f2e799 | grep -v -E "^\s+- (img|generic)" | head -60
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
$ ./browse click f2e494 | grep -v -E "^\s+- (img|generic)" | head -30
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1125]:
    - banner [ref=f2e419]:
          - button "Close" [ref=f2e424] [cursor=pointer]
      - paragraph [ref=f2e1129]: Created configuration for Solar.
      - button "Finish" [ref=f2e1132] [cursor=pointer]
```

```
$ ./browse click f2e1132 | grep -i -E "solar" | head
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
$ ./browse done "Added Solar connected to Inverter (DC) with all 32 Forecast.Solar sensors (east/north/south/west × 8 days); Solar now appears in Home."
```

```
Recorded. You can stop now.
```

I added a Solar element to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors each. For each direction those are today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element again after saving to check its settings.

I chose Inverter (DC) as the connection because it was already selected and your panels feed the inverter. I left the Curtailment section alone.

Points where I hesitated or was unsure:
- **"Add all" count:** With no search text, "Add all" offered 38 sensors. The extra 6 were Sigen plant sensors, which aren't Forecast.Solar. I typed "energy_production" into the search first, which narrowed the list to 32, and then used "Add all".
- **South sensor names:** The south sensors are named "South solar prediction forecast" rather than "solar production forecast". Their entity IDs match the others, so I included them.
- **Combined forecast chart:** After adding the sensors, the dialog showed a combined forecast chart (0 kW to 17.9 kW over the next 168 hours). I took that as a sign they were read correctly but didn't check it further.


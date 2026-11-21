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

Inverter is already selected. Open the forecast picker.

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
$ ./browse look | grep -n -E "Add all|option" | head -5; ./browse look | grep -c "option \"Forecast"
```

```
49:                    - option "Add all 32" [ref=f2e799] [cursor=pointer]
50:                    - option "Forecast East solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_east" [ref=f2e504] [cursor=pointer]:
55:                    - option "Forecast East solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_east" [ref=f2e512] [cursor=pointer]:
60:                    - option "Forecast East solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_east" [ref=f2e520] [cursor=pointer]:
65:                    - option "Forecast East solar production forecast Estimated energy production - 6 days from now sensor.energy_production_d6_east" [ref=f2e528] [cursor=pointer]:
32
```

```
$ ./browse click f2e799 | grep -v -E "^\s+- (generic|img)" | tail -40
```

```
            - button [expanded] [ref=f2e473] [cursor=pointer]:
              - heading "Forecast" [level=3] [ref=f2e474]
            - region "Forecast" [ref=f2e476]:
                    - button "Remove East solar production forecast Estimated energy production - 3 days from now" [ref=f2e807] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 4 days from now" [ref=f2e817] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 5 days from now" [ref=f2e827] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 6 days from now" [ref=f2e837] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 7 days from now" [ref=f2e847] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - day after tomorrow" [ref=f2e857] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - today" [ref=f2e866] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - tomorrow" [ref=f2e876] [cursor=pointer]
                    - button "Remove North solar production forecast Estimated energy production - 3 days from now" [ref=f2e886] [cursor=pointer]
... (28 more lines in actions.jsonl)
```

All 32 added. Submit.

```
$ ./browse click f2e494 | grep -v -E "^\s+- (generic|img)" | head -30
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
$ ./browse click f2e1132 | grep -E "Solar" | head
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
$ ./browse done "Added Solar element connected to Inverter with all 32 Forecast.Solar energy production sensors (east, north, south, west × 8 days each); config created and Solar now appears under Home."
```

```
Recorded. You can stop now.
```

I added a Solar element to the "Home" hub, connected to the Inverter, with all 32 Forecast.Solar sensors. That is 8 sensors for each of east, north, south and west: today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under Home. I didn't open the new element again to check its saved settings.

I left the connection on the default, Inverter. Your panels feed into the inverter, so that matched.

Points where I hesitated:
- **"Add all" button:** With an empty search it offered 38 entities, which included Sigen Plant sensors that aren't Forecast.Solar. I typed "energy_production" first, so the button added exactly the 32 forecast sensors.
- **South sensor names:** The south sensors are named "South solar prediction forecast" while the others say "production forecast". Their entity IDs follow the same `energy_production_*_south` pattern, so I included them.


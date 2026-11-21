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

Inverter connection is selected already. Open forecast picker.

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
... (241 more lines in actions.jsonl)
```


```
$ ./browse click f2e547
```

```
Clicked f2e547.

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
... (50 more lines in actions.jsonl)
```


```
$ ./browse click f2e485 | grep -c "option " ; ./browse look | grep -E "option \"" | head -5
```

```
0
```

```
$ ./browse type f2e485 energy_production_ | grep -E "option |combobox" | cut -c1-200
```

```
                  - 'combobox "Forecast: search entities or enter a value" [expanded] [ref=f2e485]': energy_production_
                    - option "Add all 31" [ref=f2e814] [cursor=pointer]
                    - option "Forecast East solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_east" [ref=f2e819] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_east" [ref=f2e827] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_east" [ref=f2e835] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 6 days from now sensor.energy_production_d6_east" [ref=f2e843] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 7 days from now sensor.energy_production_d7_east" [ref=f2e851] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - day after tomorrow sensor.energy_production_d2_east" [ref=f2e859] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - tomorrow sensor.energy_production_tomorrow_east" [ref=f2e867] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_north" [ref=f2e875] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_north" [ref=f2e883] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_north" [ref=f2e891] [cursor=pointer]:
... (21 more lines in actions.jsonl)
```

"Add all 31" — exactly the remaining ones.

```
$ ./browse click f2e814 | grep -E "Remove|Combined|error|Submit" | cut -c1-160
```

```
                    - button "Remove East solar production forecast Estimated energy production - today" [ref=f2e800] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 3 days from now" [ref=f2e1071] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 4 days from now" [ref=f2e1081] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 5 days from now" [ref=f2e1091] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 6 days from now" [ref=f2e1101] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 7 days from now" [ref=f2e1111] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - day after tomorrow" [ref=f2e1121] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - tomorrow" [ref=f2e1131] [cursor=pointer]
                    - button "Remove North solar production forecast Estimated energy production - 3 days from now" [ref=f2e1141] [cursor=pointer]
                    - button "Remove North solar production forecast Estimated energy production - 4 days from now" [ref=f2e1151] [cursor=pointer]
                    - button "Remove North solar production forecast Estimated energy production - 5 days from now" [ref=f2e1161] [cursor=pointer]
                    - button "Remove North solar production forecast Estimated energy production - 6 days from now" [ref=f2e1171] [cursor=pointer]
... (22 more lines in actions.jsonl)
```

All 32 added. Submit.

```
$ ./browse click f2e494 | cut -c1-200 | head -40
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1380]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1381]
    - generic [ref=f2e1382]:
      - paragraph [ref=f2e1384]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e1387 | grep -i -E "solar" | head
```

```
          - button "Solar" [ref=f2e114] [cursor=pointer]
                          - generic: Solar
                      - generic: Solar
                      - generic: Solar
                        - generic "Solar" [ref=f2e1392]:
                          - button "Solar" [ref=f2e1393] [cursor=pointer]
                      - generic: Solar
```

```
$ ./browse done "Added Solar element to Home, connected to Inverter (DC), with all 32 Forecast.Solar sensors (east/north/south/west × today, tomorrow, day after tomorrow, days 3-7). Success shown and Solar appears in the hub."
```

```
Recorded. You can stop now.
```

I added a Solar element to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors. Home Assistant showed "Created configuration for Solar", and Solar now appears under the hub. I didn't open the saved Solar entry again to re-read the sensor list. The forecast preview in the form summed all of them, rising to 17.9 kW over the next 168 hours.

The 32 sensors are the four directions (east, north, south, west) times eight days each: today, tomorrow, the day after tomorrow, and 3 to 7 days from now.

The Connection field already defaulted to Inverter, which matches your panels feeding into it, so I left it. I picked one sensor first and then used the "Add all 31" option to add the rest.

Points where I hesitated or was unsure:
- **Connection:** I kept the default Inverter (DC) rather than Switchboard (AC). It matches your description, but I never opened the Switchboard option to compare.
- **Skipped Curtailment:** I left the Curtailment section collapsed, since you didn't ask for it.
- **Which sensors counted:** The picker also listed unrelated Sigen sensors, such as Sigen Plant PV Power. I left them out because you asked for the Forecast.Solar ones only. I took "every day it covers" to mean all eight days per direction.


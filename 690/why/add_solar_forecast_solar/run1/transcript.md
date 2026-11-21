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

Inverter, DC is already selected. Open the forecast picker.

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
$ ./browse click f2e499
```

```
Clicked f2e499.

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
$ ./browse click f2e485 | grep -c "option \"Forecast"; ./browse type f2e485 energy_production_d3 | grep -E "option|combobox" | head -20
```

```
0
                  - 'combobox "Forecast: search entities or enter a value" [expanded] [ref=f2e485]': energy_production_d3
                    - option "Add all 3" [ref=f2e815] [cursor=pointer]
                    - option "Forecast North solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_north" [ref=f2e820] [cursor=pointer]:
                    - option "Forecast South solar prediction forecast Estimated energy production - 3 days from now sensor.energy_production_d3_south" [ref=f2e828] [cursor=pointer]:
                    - option "Forecast West solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_west" [ref=f2e836] [cursor=pointer]:
```

An "Add all" option. Try searching "energy_production_" to add all at once.

```
$ ./browse type f2e485 sensor.energy_production | grep -E "Add all|combobox"
```

```
                  - 'combobox "Forecast: search entities or enter a value" [expanded] [ref=f2e485]': sensor.energy_production
                    - option "Add all 31" [ref=f2e844] [cursor=pointer]
```

```
$ ./browse click f2e844 | grep -E "Remove|img \"Comb" | wc -l; ./browse look | grep -E "img \"Comb|Remove" | head -3
```

```
33
                    - button "Remove East solar production forecast Estimated energy production - 3 days from now" [ref=f2e801] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 4 days from now" [ref=f2e1072] [cursor=pointer]
                    - button "Remove East solar production forecast Estimated energy production - 5 days from now" [ref=f2e1082] [cursor=pointer]
```


```
$ ./browse look | grep -E "Remove" | wc -l; ./browse look | grep -E "Submit"
```

```
32
      - button "Submit" [ref=f2e494] [cursor=pointer]
```

```
$ ./browse click f2e494 | head -40
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
$ ./browse click f2e1387 >/dev/null; ./browse done "Added Solar (connected to Inverter, DC) with all 32 Forecast.Solar sensors (east/north/south/west, 8 each) as forecast."
```

```
Recorded. You can stop now.
```

I added the solar to HAEO as "Solar", connected to the Inverter (DC). It uses all 32 Forecast.Solar sensors as its forecast. That is 8 for each of east, north, south and west: today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar." I didn't reopen the entry afterwards to check it, but the forecast field listed 32 sensors before I submitted.

I left the name as "Solar" and didn't open the Curtailment section.

Points where I hesitated or was unsure:
- **Connection:** "Inverter, DC" was already selected by default. I kept it because your panels feed into the inverter.
- **Adding the sensors:** The forecast field accepts several sensors. I added the first one by hand, then searched "sensor.energy_production" and used the "Add all 31" option for the rest. I counted 32 remove buttons afterwards to confirm none were missed.
- **Sensor choice:** I assumed every `sensor.energy_production_*` entry was a Forecast.Solar sensor. None of the other sensors in the list (the Sigen plant ones) matched that search.


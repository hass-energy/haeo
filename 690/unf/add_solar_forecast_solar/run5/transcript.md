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
$ ./browse look | grep -E "Add all|option" | cut -c1-150 | head -50
```

```
                    - option "Add all 32" [ref=f2e799] [cursor=pointer]
                    - option "Forecast East solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_east" 
                    - option "Forecast East solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_east" 
                    - option "Forecast East solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_east" 
                    - option "Forecast East solar production forecast Estimated energy production - 6 days from now sensor.energy_production_d6_east" 
                    - option "Forecast East solar production forecast Estimated energy production - 7 days from now sensor.energy_production_d7_east" 
                    - option "Forecast East solar production forecast Estimated energy production - day after tomorrow sensor.energy_production_d2_eas
                    - option "Forecast East solar production forecast Estimated energy production - today sensor.energy_production_today_east" [ref=f2
                    - option "Forecast East solar production forecast Estimated energy production - tomorrow sensor.energy_production_tomorrow_east" [
                    - option "Forecast North solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_north
                    - option "Forecast North solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_north
                    - option "Forecast North solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_north
... (21 more lines in actions.jsonl)
```

All 32 are the right ones.

```
$ ./browse click f2e799 | grep -vE "option|img|generic \[ref=f2e[0-9]+\]: (East|North|South|West|sensor)" | head -60
```

```
Clicked f2e799.

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
... (48 more lines in actions.jsonl)
```

```
$ ./browse look | grep -c 'button "Remove'; ./browse look | grep -E "Submit"
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
$ ./browse done "Added Solar to Home, connected to Inverter, with all 32 Forecast.Solar sensors (east/north/south/west × today, tomorrow, day after tomorrow, d3–d7). Solar now appears in the hub."
```

```
Recorded. You can stop now.
```

I added Solar to the Home hub. It's connected to the Inverter and uses all 32 Forecast.Solar sensors. That's east, north, south and west, each for today, tomorrow, the day after tomorrow and days 3 to 7. Home Assistant showed "Created configuration for Solar", and Solar now appears in the hub list. I didn't open the new entry to check its settings.

Points where I hesitated or took a risk:
- **"Add all" button:** With nothing typed, the picker offered "Add all 38". The extra six were Sigen Plant sensors (consumed power, PV power and so on), which aren't Forecast.Solar sensors. I typed "energy_production" first, so the button became "Add all 32". I checked that all 32 were the East, North, South and West forecast sensors, then clicked it. I also counted 32 remove buttons in the field before submitting.
- **Connection:** I left the connection on Inverter (DC), which was already selected. It matches rooftop solar feeding the inverter. I didn't change it or look at the Switchboard option beyond reading the label.
- **Name and other settings:** I kept the default name "Solar". I left the Curtailment section closed and untouched.


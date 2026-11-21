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
$ ./browse look | grep -n -i -E "add all|option" | head -8
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

Add all 32 is exactly the Forecast.Solar set.

```
$ ./browse click f2e799 | grep -v -E "option|img|generic \[ref=f2e[5-7]" | head -60
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
$ ./browse look | grep -c 'button "Remove'; ./browse click f2e494 | head -40
```

```
32
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
... (2 more lines in actions.jsonl)
```

```
$ ./browse click f2e1132 | grep -i -c solar
```

```
$ ./browse done "Added Solar element connected to Inverter with all 32 Forecast.Solar sensors (east/north/south/west x 8 days)."
```

```
7
```

```
Recorded. You can stop now.
```

I added a "Solar" element to HAEO and connected it to the Inverter. It uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 sensors per direction. Those 8 are today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and I counted 32 entries in the forecast field before submitting.

I didn't reopen the Solar element afterwards to check the saved values.

Points where I hesitated or could have gone wrong:
- **Connection:** I kept the default, Inverter, and didn't change it. The picture for that option showed Battery and a sun icon, which matches panels feeding the inverter. The other option was Switchboard.
- **"Add all":** The unfiltered picker offered "Add all 38". That count also included Sigen Plant sensors, such as PV power and consumed power. I typed "energy_production" first, so "Add all" covered exactly 32 sensors.
- **Curtailment:** I left the Curtailment section closed and untouched. I wasn't asked about it.


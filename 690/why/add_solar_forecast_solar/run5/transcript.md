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

Inverter is selected by default, which is right (feeds the inverter).

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
$ ./browse click f2e499 | grep -v "option\|img\|generic \[ref=f2e[5-9]" | head -60
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
... (43 more lines in actions.jsonl)
```

Multi-select. Let me add the rest by searching.

```
$ ./browse click f2e485 >/dev/null; ./browse type f2e485 energy_production_ | grep -c "option "; ./browse look | grep -E "option " | head -50
```

```
32
                    - option "Add all 31" [ref=f2e815] [cursor=pointer]
                    - option "Forecast East solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_east" [ref=f2e820] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_east" [ref=f2e828] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 6 days from now sensor.energy_production_d6_east" [ref=f2e836] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - 7 days from now sensor.energy_production_d7_east" [ref=f2e844] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - day after tomorrow sensor.energy_production_d2_east" [ref=f2e852] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - today sensor.energy_production_today_east" [ref=f2e860] [cursor=pointer]:
                    - option "Forecast East solar production forecast Estimated energy production - tomorrow sensor.energy_production_tomorrow_east" [ref=f2e867] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 3 days from now sensor.energy_production_d3_north" [ref=f2e875] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 4 days from now sensor.energy_production_d4_north" [ref=f2e883] [cursor=pointer]:
                    - option "Forecast North solar production forecast Estimated energy production - 5 days from now sensor.energy_production_d5_north" [ref=f2e891] [cursor=pointer]:
... (21 more lines in actions.jsonl)
```

"Add all 31" matches exactly the remaining ones.

```
$ ./browse click f2e815 | grep -E "Remove|Forecast \*" | wc -l
```

```
33
```

```
$ ./browse look | grep -E "Remove|Submit|error" | grep -c Remove; ./browse look | grep Submit
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
- alertdialog "Success" [ref=f2e1379]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1380]
    - generic [ref=f2e1381]:
      - paragraph [ref=f2e1383]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e1386 >/dev/null; ./browse done "Added Solar connected to Inverter (DC) with all 32 Forecast.Solar energy production sensors (east, north, south, west × today, tomorrow, d2–d7)."
```

```
Recorded. You can stop now.
```

I added a Solar element to the Home hub, connected to the Inverter, and used all 32 Forecast.Solar energy production sensors. That is east, north, south and west, each with today, tomorrow and days 2 to 7. The wizard ended with "Created configuration for Solar."

I didn't reopen the Solar entry afterwards to check the saved list. The only check was that the form showed 32 selected sensors before I submitted.

Points where I hesitated or made a mistake:
- **Connection:** I left it on "Inverter" (the default) rather than "Switchboard". You said the panels feed the inverter, so I'm fairly sure that's right, but I didn't compare the two options further.
- **Sensor count:** I selected the first sensor by hand, then used "Add all 31" after searching `energy_production_`. I checked that the list was exactly the 31 remaining Forecast.Solar sensors before clicking.
- **Unrelated sensors:** The picker also listed Sigen Plant power sensors, which I ignored because they aren't Forecast.Solar forecasts.
- **Curtailment:** I left that section collapsed and untouched.


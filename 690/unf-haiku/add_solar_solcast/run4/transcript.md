# Transcript


*Show current HAEO integration page*
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


*Click Solar button to add a solar element*
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


The solar panels feed the inverter, so the default "Inverter, DC" connection is right. Next I'll find the Solcast forecast sensors.

*Open forecast picker and search for solcast*
```
$ ./browse click f2e485 && ./browse type f2e485 "solcast"
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
... (161 more lines in actions.jsonl)
```


The three Solcast sensors (today, tomorrow, day 3) are listed. I'll use "Add all 3" so the forecast covers all three.

*Add all three Solcast forecast sensors*
```
$ ./browse click f2e562
```

```
Clicked f2e562.

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
... (60 more lines in actions.jsonl)
```


All three sensors are in the forecast and the combined preview shows values. I'll leave Curtailment at its default since you didn't ask for it, and submit.

*Submit the solar configuration*
```
$ ./browse click f2e494
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e601]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e602]
    - generic [ref=f2e603]:
      - paragraph [ref=f2e605]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e608
```

```
Clicked f2e608.

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
... (352 more lines in actions.jsonl)
```

I added the solar element to the Home hub and it's now listed as a "Solar" device with 4 entities. The count went from 57 to 61 entities.

Settings I chose:
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default). Your panels feed the inverter, so this is the right connection.
- **Forecast:** all three Solcast sensors, added with "Add all 3": `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`. The preview showed a combined forecast of 0 kW now, rising to 23.2 kW over the next 72 hours.
- **Curtailment:** left at default, since you didn't ask for it.

I didn't open the new Solar device afterwards to confirm its entity values, so the check that it took effect is the entity count and the success dialog.

Where I hesitated or was unsure:
- I wasn't sure whether the Solcast sensors should be added as three separate forecasts or as one combined list. I used "Add all 3" because the three sensors together make up one PV forecast over time.
- I left Curtailment alone. I didn't check whether it matters for a rooftop system that sends its surplus to the grid, so it may need a look.
- The Connection choice relied on the label "Inverter, DC" matching your wiring. I didn't have a wiring diagram to confirm it.


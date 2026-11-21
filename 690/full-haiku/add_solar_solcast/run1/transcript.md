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

The HAEO page shows a "Solar" button under "Add hub". I'll open it.

*Click Solar add button*
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


The solar config dialog is open. Solar panels feed the inverter on DC, so the default "Inverter, DC" connection is right. Next I'll find the Solcast sensors in the forecast picker.

*Open forecast entity picker*
```
$ ./browse click f2e485
```

*Search forecast picker for Solcast*
```
$ ./browse type f2e485 Solcast
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
... (92 more lines in actions.jsonl)
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
... (57 more lines in actions.jsonl)
```


The search shows exactly the three Solcast forecast sensors (today, tomorrow, day 3). I'll use "Add all 3".

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


All three forecasts are added, and the chart preview shows a combined forecast up to 23.2 kW. The name, connection and curtailment defaults look right, so I'll submit.

*Submit solar configuration*
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


The Solar element is added to Home and uses the three Solcast PV forecast sensors.

- **Connection:** Inverter, DC (the default). Your panels feed the inverter, so this is the right choice.
- **Forecast:** `sensor.solcast_pv_forecast_forecast_today`, `sensor.solcast_pv_forecast_forecast_tomorrow` and `sensor.solcast_pv_forecast_forecast_day_3`, added with "Add all 3".
- **Name:** Solar (default).
- **Curtailment:** left at its defaults.

The success dialog reported "Created configuration for Solar", and the Home hub now lists a Solar device with 4 entities. The forecast preview showed a combined range of 0 to 23.2 kW over 72 hours.

Points where I hesitated or may have made a mistake:
- I accepted the default name "Solar" without thinking about whether you'd want a different label.
- I left the Curtailment section untouched. I didn't open it, so I don't know whether your inverter needs any curtailment setting. You may want to check it.
- I didn't open the Solar device after saving to confirm the stored forecast sensors, so I'm relying on the picker and preview rather than a saved-config check.
- The Solcast sensor names and the "Add all 3" option were clear enough that I didn't need to pick them one by one. That shortcut could have included a wrong sensor if more Solcast sensors had been present, but only three appeared.


# Transcript


*Show current page accessibility tree*
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

There's an "Add hub" button and a "Solar" button under the hub-type list. I'll click "Solar" to add the solar element.

*Click the Solar element button*
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


The solar feeds the inverter, so the default "Inverter, DC" connection fits. Next I'll open the Forecast field to find the Forecast.Solar sensors.

*Open the Forecast entity picker*
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


The list includes 38 entities, and six of them are Sigen sensors that aren't Forecast.Solar. I'll filter the search to `energy_production` so that only the Forecast.Solar sensors remain.

*Filter the forecast picker to energy_production sensors*
```
$ ./browse type f2e485 "energy_production"
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
... (202 more lines in actions.jsonl)
```


The filter shows "Add all 32", which is 4 directions × 8 forecast sensors each, and that matches the four-direction Forecast.Solar layout. I'll add them all.

*Click Add all 32 forecast sensors*
```
$ ./browse click f2e799
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
... (205 more lines in actions.jsonl)
```


All 32 Forecast.Solar sensors are now in the Forecast list, and the combined preview shows a forecast curve. Curtailment is collapsed and I'll leave it at its default. Submitting now.

*Submit the solar configuration*
```
$ ./browse click f2e494
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

*Click Finish on the success dialog*
```
$ ./browse click f2e1132
```

```
Clicked f2e1132.

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


I added the solar element to HAEO as "Solar" with all 32 Forecast.Solar production sensors: 8 for each of east, north, south and west. The integration page now shows a Solar device with 4 entities.

**Points where I hesitated or was unsure:**

- **Connection:** I kept the default "Inverter, DC" because you said the panels feed the inverter. I did not check whether your inverter is DC-coupled to the battery. If the panels are wired to the AC side, "Switchboard, AC" would be the right choice instead.
- **Sensor selection:** The unfiltered picker offered "Add all 38". Six of those were Sigen sensors, not Forecast.Solar, so I typed `energy_production` to narrow the list to 32 before adding them. I then checked that the 32 matched the four directions with eight day-sensors each.
- **South naming:** The south sensors are labelled "solar prediction forecast" while the others say "solar production forecast". They have the same `energy_production_*_south` entity ID pattern, so I treated them as Forecast.Solar and included them. Worth a quick check.
- **Curtailment:** I left this collapsed at its default and did not look at it. I don't know whether your inverter needs a curtailment setting.
- **Name:** I kept the default name "Solar" without thinking about whether a different name would be clearer.
- **Verification:** I confirmed the device and entity count on the integration page, but did not open the Solar device to check the forecast values or the individual entity states.


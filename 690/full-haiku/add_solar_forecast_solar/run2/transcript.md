# Transcript


*Show current HAEO page*
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


*Open the forecast entity picker*
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


*Filter the forecast picker to Forecast.Solar sensors*
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


The filter narrows the list to exactly the 32 Forecast.Solar sensors (8 per direction), without the Sigen sensors. I'll use "Add all 32".

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


All 32 Forecast.Solar sensors are in the list (8 per direction, none of the Sigen sensors). The connection is Inverter, which matches panels feeding the inverter. I'll submit.

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


I added the solar element "Solar" to your Home hub, connected to the Inverter as DC, with all 32 Forecast.Solar sensors. HAEO reported "Created configuration for Solar", and the Home hub now lists a Solar device with 4 entities.

**Points where I hesitated or was unsure:**

1. **Connection type:** The picker offered "Inverter, DC" and "Switchboard, AC". You said the panels feed the inverter, so I kept the default Inverter (DC). If your inverter is AC-coupled to the switchboard, this would need to change.
2. **Sensor selection:** The unfiltered forecast list mixed in six Sigen sensors (consumed power, ESS ratings, PV power and so on) alongside the Forecast.Solar ones. "Add all 38" would have included them. I typed "energy_production" to narrow the list to the 32 Forecast.Solar sensors (8 per direction: today, tomorrow, day after tomorrow, and 3 to 7 days out), then used "Add all 32". I checked the resulting list and it contains only those sensors.
3. **Sensor naming:** The South sensors are labelled "South solar prediction forecast" rather than "production forecast" like the others. I took them to be the same kind of Forecast.Solar estimate, since they share the `energy_production_*` pattern. I did not verify this further.
4. **Name and curtailment:** I left the name as the default "Solar" and did not open the Curtailment section, since you didn't ask for anything there.
5. **Result check:** The preview chart showed a combined forecast of 0 kW now, rising to 17.9 kW. I did not check the values against your known panel output.


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

The HAEO page is open with the Home hub. I'll click the "Solar" button in the "Add hub" section to start a new Solar element.

*Click Solar element button*
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


The form defaults to the Inverter (DC) connection, which matches "feeds into your inverter", so I'll keep it. Next I'll open the Forecast picker to see the Forecast.Solar sensors.

*Open forecast entity picker*
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


The picker lists 38 entities. Thirty-two of them are Forecast.Solar `energy_production_*` sensors (today, tomorrow, and days 2–7 for each of the four directions). The other six are Sigen sensors, so I shouldn't use "Add all 38". I'll filter the picker to the Forecast.Solar sensors first.

*Filter forecast picker to energy_production sensors*
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


The filter now shows "Add all 32", which matches exactly the 32 Forecast.Solar sensors (8 per direction) and excludes the Sigen sensors. I'll click it.

*Click Add all 32 filtered forecast sensors*
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


All 32 Forecast.Solar sensors are in the Forecast field, and the combined preview is showing. Curtailment is optional and I have no basis to change it, so I'll leave it alone and submit.

*Submit solar configuration*
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

*Click Finish on success dialog*
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


I added the solar element "Solar" to the Home hub with all 32 Forecast.Solar sensors. HAEO created it and it now appears in the hub's device list.

- **Connection:** Inverter (DC), the default. I read "feeds into your inverter" as DC-coupled panels behind the inverter. If your panels actually feed the AC side (Switchboard), this is the setting to change.
- **Sensors:** The picker listed 38 entities, but only 32 are Forecast.Solar. Those are `energy_production_*` for today, tomorrow and days 2–7 in each of East, North, South and West. I filtered the list to `energy_production` and used "Add all 32". I did not use "Add all 38", which would also have added six Sigen sensors.
- **Curtailment:** Left at its default because I had no information about it.
- **Name:** Left as "Solar".

I did not open the Solar device afterwards to confirm all 32 sensors were saved. The preview chart showed the combined forecast (0 kW now, up to 17.9 kW), and the success dialog confirmed creation.

Points where I hesitated or was unsure:
- The Connection choice was an inference from your description, not something the form made obvious. I'm least sure of this one.
- The South sensors are labelled "solar prediction forecast" while the others say "solar production forecast". I treated them as the same Forecast.Solar sensors because they share the `energy_production_*_south` naming.
- I did not check the sensor count on the saved element. The 32 I added came from the "Add all 32" count and the visible list.
- I used "Add all 32" on a filtered list rather than clicking sensors one at a time. That was faster, and I checked the result before submitting.
- The HAEO page shows 4 entities under the new Solar device. I did not look into what those four are.


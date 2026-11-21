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


The integration page has a "Load" element type to add. I'll open it.

*Click the Load element type button*
```
$ ./browse click f2e108
```

```
Clicked f2e108.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Load configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (44 more lines in actions.jsonl)
```


The form has a name, a connection (Switchboard is preselected), and a Forecast entity field. I'll rename the load to "Household" and search for the Sigenergy forecast sensor.

*Rename load and search forecast entities for consumed*
```
$ ./browse type f2e445 "Household" && ./browse click f2e487 && ./browse type f2e487 "consumed"
```

```
Typed into f2e445.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Load configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (374 more lines in actions.jsonl)
```


The Forecast search shows the Sigen "Consumed Power Forecast" sensor. I'll select it.

*Select Sigen consumed power forecast sensor*
```
$ ./browse click f2e639
```

```
Clicked f2e639.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Load configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (55 more lines in actions.jsonl)
```


The forecast is set and the field now shows a combined preview. Next I'll add the current consumed power sensor to the same field, since the field accepts multiple sources.

*Search for current consumed power sensor in forecast field*
```
$ ./browse click f2e487 && ./browse type f2e487 "Sigen Plant Consumed Power"
```

```
Clicked f2e487.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Load configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (126 more lines in actions.jsonl)
```

*Select current consumed power sensor*
```
$ ./browse click f2e823
```

```
Clicked f2e823.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Load configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (62 more lines in actions.jsonl)
```


Both sources are now in the field. The preview shows the current value at "now" and the forecast for later intervals. I'll submit.

*Submit the load configuration*
```
$ ./browse click f2e496
```

```
Clicked f2e496.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e848]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e849]
    - generic [ref=f2e850]:
      - paragraph [ref=f2e852]: Created configuration for Household.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e855
```

```
Clicked f2e855.

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


*Report completion of the household load setup*
```
$ ./browse done "Added a Load named 'Household' to the Home hub: connection Switchboard (AC), with forecast sources sensor.sigen_plant_consumed_power_forecast and the current value sensor.sigen_plant_consumed_power. The Home hub now lists a Household Load device with 12 entities. Shedding was left at its default."
```

```
Recorded. You can stop now.
```

I added a Load named "Household" to the Home hub. It is connected to the Switchboard (AC) and takes both Sigen consumed-power sensors as its forecast input. The Home hub now lists a Household Load device with 12 entities.

Points where I hesitated, was unsure, or may have made a mistake:

1. **Load name:** The default was "Load". I renamed it to "Household" to match what it represents. That is a judgment call, and you can change it.
2. **Connection:** Switchboard (AC) was preselected. I kept it because household consumption sits on the AC side, but I did not check this against your wiring.
3. **Current sensor placement:** The form had only one "Forecast" field, with no separate field for a current value. I added `sensor.sigen_plant_consumed_power` to that same field, beside the forecast sensor. The preview then showed the current value for "now" and the forecast for later intervals. I assumed that is the intended way to combine them, but I did not confirm it in the HAEO docs, which I did not have.
4. **Shedding:** I left the Shedding section collapsed at its defaults. I did not look at what it controls, because you did not ask for it.
5. **Verification:** I confirmed the success message and the new device on the hub page. I did not reopen the Household load to check the saved forecast entries.


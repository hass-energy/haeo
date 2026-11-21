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


*Click Load to add a load element*
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


*Rename load to Household and open forecast picker*
```
$ ./browse type f2e445 "Household" && ./browse click f2e487
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
... (303 more lines in actions.jsonl)
```


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


*Search forecast picker for current consumed power sensor*
```
$ ./browse click f2e487 && ./browse type f2e487 "sigen_plant_consumed_power"
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


*Select current consumed power sensor to see combined preview*
```
$ ./browse click f2e822
```

```
Clicked f2e822.

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


The combined preview now reads "now 0.501 kW, then 0 kW to 1.66 kW", so the current sensor covers the present and the Sigen forecast covers the future. Submitting.

*Submit the load configuration*
```
$ ./browse click f2e496
```

```
Clicked f2e496.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e847]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e848]
    - generic [ref=f2e849]:
      - paragraph [ref=f2e851]: Created configuration for Household.
... (1 more lines in actions.jsonl)
```

*Finish the add-load flow*
```
$ ./browse click f2e854
```

```
Clicked f2e854.

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


I added a Household load to the Home hub and it saved as "Created configuration for Household." The new Household device now appears under Home with 12 entities.

- **Load name:** I renamed the default "Load" to "Household" so it's clear what the element represents.
- **Connection:** I kept the default, Switchboard (AC). Household consumption sits on the AC side, so this seemed right.
- **Forecast:** I selected `sensor.sigen_plant_consumed_power_forecast` as the forecast.
- **Current consumed power:** The form has no separate "current" field. I added `sensor.sigen_plant_consumed_power` to the same Forecast list. The combined preview changed from "now 0.4 kW" to "now 0.501 kW, then 0 kW to 1.66 kW", so the current reading covers the present and the Sigen forecast covers the future.
- **Not checked:** I didn't open the saved Household configuration afterwards to confirm both sensors were stored, and I didn't check whether HAEO sums the two sources or uses the current value only for "now".

Points where I hesitated or was unsure:
1. The form only offers a single "Forecast" field, so I had to decide that putting the current sensor there was the intended way to use it. I chose it because the preview's "now" value changed to match the current reading.
2. I wasn't sure whether the two sensors would be double-counted. The preview suggests they are not, but I couldn't confirm the optimizer's behaviour.
3. I left the Shedding section alone because it is not part of this request and I don't know what it controls.
4. I chose the name "Household" myself. You may prefer a different name.


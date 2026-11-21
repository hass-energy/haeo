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


The integration page lists a "Load" element type. I'll add that as the household consumption element.

*Click the Load element button to add a load*
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


The form has a name, a connection (Switchboard is already selected, which fits a household load on the AC side), and a required Forecast field. I'll give it a clearer name and then look at the Forecast picker.

*Rename load to Household and open forecast entity picker*
```
$ ./browse type f2e445 "Household"; ./browse click f2e487
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


The forecast sensor is `sensor.sigen_plant_consumed_power_forecast`, and the current value sensor is `sensor.sigen_plant_consumed_power`. I'll select the forecast one first and see how the field handles a second entity.

*Select Sigen Plant Consumed Power Forecast sensor*
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


The Forecast field takes several sensors and shows a combined preview. I'll add the current consumed power sensor and check what the preview does with it.

*Open forecast picker and search for consumed power*
```
$ ./browse click f2e487; ./browse type f2e487 "consumed power"
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

*Select Sigen Plant Consumed Power current value sensor*
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


The combined preview now reads "now 0.501 kW, then 0 kW to 1.66 kW". The current sensor is replacing the forecast's "now" value rather than being added to it, which is the behaviour I wanted. I'll leave Shedding at its default and submit.

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

*Click Finish on success dialog*
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


*Finish with summary of the added household load*
```
$ ./browse done "Added a Load element named 'Household' to the Home HAEO hub. Connection: Switchboard (AC), which was already selected by default. Forecast: sensor.sigen_plant_consumed_power_forecast plus sensor.sigen_plant_consumed_power as the current value. The combined preview shows 'now 0.501 kW, then 0 kW to 1.66 kW', so the current reading replaces the forecast for the present moment and is not added to it. Shedding left at default. Household now appears under the Home hub with 12 entities."
```

```
Recorded. You can stop now.
```

I added a household load to the Home hub. It's named "Household", uses the Switchboard (AC) connection, and has both your Sigen consumed power sensors as its forecast input. The success dialog confirmed creation, and "Household" now appears under the Home hub.

**Points where I hesitated or was unsure:**

1. **Element type.** The integration page offers a "Load" element, and I used it for household consumption. I didn't find a more specific option, so this was my judgement call.
2. **Name.** The form defaulted to "Load". I renamed it to "Household" so it's distinguishable from the other elements.
3. **Connection.** Switchboard (AC) was pre-selected. A household load sits on the AC side, so I kept it, but I didn't change or check the alternatives.
4. **Where the current sensor goes.** The form has only one "Forecast" field, and it accepts several sensors. I didn't see a separate "current power" field, so I added `sensor.sigen_plant_consumed_power` alongside the forecast. Once I did, the preview switched "now" to 0.501 kW and kept the forecast for later intervals. I read that as the current reading replacing the forecast's present value, not being summed with it, but I inferred that from the preview only. The help text didn't say it explicitly.
5. **Shedding.** I left the Shedding section at its defaults without reading what it does. I didn't judge whether household load should be sheddable.
6. **Verification.** I confirmed the entry was created and that the Household device shows 12 entities. I did not check the individual entity values or how the optimiser uses this load.


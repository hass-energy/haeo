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


*Search for the current consumed power sensor*
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

*Select current Sigen Plant Consumed Power sensor*
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

*Finish and close the success dialog*
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


*Finish with summary of the added load*
```
$ ./browse done "Added a Load element named 'Household' to the Home hub. Connection is Switchboard (AC), the default and the right side for household consumption. Forecast takes two sensors: sensor.sigen_plant_consumed_power_forecast and sensor.sigen_plant_consumed_power (current value). Shedding left at default. The success dialog said 'Created configuration for Household', and the Household load device with 12 entities now appears under Home."
```

```
Recorded. You can stop now.
```

I added a Load named "Household" to the Home hub and confirmed it appears under Home with 12 entities.

- **Connection:** Switchboard, AC. This was already selected, and it is where household consumption sits.
- **Forecast:** I added two sensors, `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power` (the current value). The form combined them into one forecast line.
- **Shedding:** Left at its default.

Points where I hesitated or was unsure:

1. **Naming:** The default name was "Load". I renamed it to "Household" because that describes the sensor, but you may prefer another name.
2. **Two sensors in one Forecast field:** The field accepted both the forecast and the current value, and I added both as you asked. I did not check how HAEO uses the current-value sensor alongside the forecast, so I can't confirm the pairing is what you intended.
3. **Connection choice:** I kept Switchboard without changing it. I'm fairly sure it's right for a household load, but I didn't check it against your wiring.
4. **Shedding:** I didn't open it, so I can't say whether the household load should be sheddable.
5. **Verification:** I checked only that the load was created. I did not open the saved configuration to confirm both sensors are still attached.


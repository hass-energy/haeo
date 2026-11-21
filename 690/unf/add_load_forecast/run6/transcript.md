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


```
$ ./browse type f2e445 Household; ./browse click f2e487
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


```
$ ./browse click f2e639 | head -80
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

```
$ ./browse type f2e487 sigen_plant_consumed_power | grep -n "option" | head
```

```
62:                    - option "Current value 0.501000 kW Sigen Plant Consumed Power sensor.sigen_plant_consumed_power" [ref=f2e822] [cursor=pointer]:
```

Adding the current consumed power sensor alongside the forecast.

```
$ ./browse click f2e822 | grep -v "^ *- generic \[ref=f2e4[0-9][0-9]\]" | sed -n 30,80p
```

```
            - button [expanded] [ref=f2e475] [cursor=pointer]:
              - heading "Forecast" [level=3] [ref=f2e476]
            - region "Forecast" [ref=f2e478]:
                  - generic [ref=f2e801]:
                    - generic [ref=f2e802]:
                      - img "Forecast" [ref=f2e803]
                      - generic [ref=f2e807]: Sigen Plant Consumed Power Forecast
                    - button "Remove Sigen Plant Consumed Power Forecast" [ref=f2e808] [cursor=pointer]
                  - generic [ref=f2e829]:
                    - generic [ref=f2e830]:
                      - img "Current value 0.501000 kW" [ref=f2e831]:
                        - generic [ref=f2e832]: "0.501"
... (12 more lines in actions.jsonl)
```

```
$ ./browse click f2e496 | head -40
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

```
$ ./browse click f2e854 | grep -i -B2 -A3 household | head -20
```

```
                    - button [ref=f2e253] [cursor=pointer]
                    - generic [ref=f2e256]:
                      - generic: Household
                      - generic: Load
                    - generic:
                      - generic:
--
                  - generic [ref=f2e273]:
                    - generic [ref=f2e275]:
                      - generic: Household
                      - generic: 12 entities
                    - generic:
... (1 more lines in actions.jsonl)
```

```
$ ./browse done "Added a Load named Household, connected to the Switchboard. Its forecast field has both sensor.sigen_plant_consumed_power_forecast and sensor.sigen_plant_consumed_power. The Household load now appears under the Home hub with 12 entities."
```

```
Recorded. You can stop now.
```

I added a Load named "Household" to the Home hub. It connects to the Switchboard and uses two Sigenergy sensors:
- `sensor.sigen_plant_consumed_power_forecast`, the consumed power forecast.
- `sensor.sigen_plant_consumed_power`, the current consumed power.

HAEO showed "Created configuration for Household", and the load now appears under the hub with 12 entities. I didn't check any of those entities' values.

Points where I hesitated or guessed:
- **Connection:** The form had Switchboard selected by default. I kept it because household consumption is a normal AC load, but I didn't check that against your wiring.
- **Name:** I changed the default "Load" to "Household". You didn't give a name, so this was my choice.
- **Single field:** The form had only one "Forecast" field, so I put the current sensor in it next to the forecast sensor. I assumed that's how HAEO wants both used. The form's preview showed a combined result starting at 0.501 kW now, which suggests it worked.
- **Shedding:** I left the optional "Shedding" section collapsed and didn't look at it.


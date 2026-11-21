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
$ ./browse click f2e487
```

```
$ ./browse look
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
... (247 more lines in actions.jsonl)
```

```
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
        - generic [ref=f2e435]:
          - paragraph [ref=f2e436]: Configure a load with forecast or constant power.
... (245 more lines in actions.jsonl)
```


```
$ ./browse click f2e639 | head -60
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
... (48 more lines in actions.jsonl)
```

Now add the current power sensor too.

```
$ ./browse type f2e487 sigen_plant_consumed_power | grep -n "option" | head
```

```
62:                    - option "Current value 0.501000 kW Sigen Plant Consumed Power sensor.sigen_plant_consumed_power" [ref=f2e822] [cursor=pointer]:
```


```
$ ./browse click f2e822 | grep -v "^ *- option" | sed -n 30,80p
```

```
                - generic [ref=f2e456]:
                  - generic [ref=f2e457]:
                    - generic [aria-hidden] [ref=f2e458]: 🔋
                    - text: Battery
                  - generic [ref=f2e459]:
                    - generic [aria-hidden] [ref=f2e460]: ☀️
                    - text: Solar
              - radio "Switchboard, AC" [checked] [ref=f2e461] [cursor=pointer]:
                - generic [ref=f2e462]: Switchboard
                - generic [ref=f2e466]:
                  - generic [ref=f2e467]:
                    - generic [aria-hidden] [ref=f2e468]: 🏭
... (33 more lines in actions.jsonl)
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
      - paragraph [ref=f2e851]: Created configuration for Load.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e854 | grep -n "Load" | head
```

```
63:          - button "Load" [ref=f2e108] [cursor=pointer]
94:                          - generic: Load
227:                      - generic: Load
228:                      - generic: Load
231:                        - generic "Load" [ref=f2e858]:
232:                          - button "Load" [ref=f2e859] [cursor=pointer]
245:                      - generic: Load
```

```
$ ./browse done "Added a Load element named 'Load' connected to Switchboard, with both Sigen Plant Consumed Power Forecast and Sigen Plant Consumed Power (current) selected as forecast sources. It now appears under the Home hub."
```

```
Recorded. You can stop now.
```

I added a Load named "Load" to the Home hub. It now appears in the hub's list of parts. I didn't open it afterwards to re-check its settings.

- **Connection:** Switchboard (AC). It was already selected, and a household load fits there.
- **Forecast field:** I picked both `sensor.sigen_plant_consumed_power_forecast` and `sensor.sigen_plant_consumed_power`, the current reading. The field took both sensors. The preview chart showed "now 0.501 kW", so the current reading was being used.

Where I hesitated or was unsure:
- I kept the default name "Load" rather than renaming it.
- I wasn't sure whether the Forecast field would accept two sensors. It did, but I don't know how HAEO combines them. The chart labelled them "Combined".
- I left the "Shedding" section alone because you didn't ask for it.


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

Multi-select. Add the current consumed power sensor too.

```
$ ./browse type f2e487 sigen_plant_consumed_power
```

```
Typed into f2e487.

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
... (59 more lines in actions.jsonl)
```

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
      - paragraph [ref=f2e851]: Created configuration for Load.
... (1 more lines in actions.jsonl)
```

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

```
$ ./browse done "Added a Load named 'Load' connected to the Switchboard, with forecast sensors sensor.sigen_plant_consumed_power_forecast and sensor.sigen_plant_consumed_power. The new Load device shows 12 entities."
```

```
Recorded. You can stop now.
```

I added a Load to HAEO's "Home" setup. It's connected to the Switchboard and uses both Sigenergy sensors:
- `sensor.sigen_plant_consumed_power_forecast` (the consumed power forecast)
- `sensor.sigen_plant_consumed_power` (the current consumed power, 0.501 kW when I added it)

The Load now shows as a new device with 12 entities. HAEO's preview combined the two sensors as "now 0.501 kW, then 0 to 1.66 kW over the next 168 hours". I didn't open the new device or check its entities' values.

Points where I hesitated or was unsure:
- **Current-power sensor in the Forecast field:** There was no separate field for it. I added it to the same multi-select Forecast field as the forecast sensor. I assumed that is how HAEO combines the two.
- **Connection and name:** I kept the default connection (Switchboard, AC) and the default name "Load". I assumed the Switchboard is the right place for household consumption.


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

Inverter connection is selected already. Open the forecast picker.

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


```
$ ./browse type f2e485 energy_production
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

```
$ ./browse click f2e799 | grep -v "option \"" | head -80
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
... (68 more lines in actions.jsonl)
```

```
$ ./browse click f2e494 | grep -c "Remove "; ./browse look | grep -E "alertdialog|Submit|error|Pick|Required" | head
```

```
0
- alertdialog "Success" [ref=f2e1125]:
```


```
$ ./browse look | head -30
```

```
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
      - button "Finish" [ref=f2e1132] [cursor=pointer]
```

```
$ ./browse click f2e1132 >/dev/null; ./browse done "Added Solar element connected to Inverter with all 32 Forecast.Solar sensors (east, north, south, west × 8 days) selected via search + Add all."
```

```
Recorded. You can stop now.
```

I've added the Solar element to HAEO. It's connected to the Inverter and uses all 32 Forecast.Solar sensors: east, north, south and west, with 8 days for each direction. HAEO showed "Created configuration for Solar", and I clicked Finish.

I selected the sensors by searching "energy_production" in the Forecast picker and clicking "Add all 32". The unfiltered "Add all" offered 38 options, because it also included six Sigen Plant sensors that aren't from Forecast.Solar. The search kept those out.

Points where I hesitated or fell short:
- **Connection:** "Inverter" was already selected as the default, and I kept it. The panels feed the inverter, so it seemed right, but I didn't compare it with the Switchboard option.
- **Sensor count:** I didn't count the selected sensors before submitting. The "Add all 32" label and the chips I saw point to the right set. I didn't reopen the Solar element afterwards to check.
- **Optional sections:** I left the Curtailment section alone.


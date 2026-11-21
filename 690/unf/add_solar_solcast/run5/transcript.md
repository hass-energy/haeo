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

Inverter already selected. Open the forecast picker.

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
... (92 more lines in actions.jsonl)
```

Multi-select appears supported. Pick the three Solcast ones.

```
$ ./browse click f2e547
```

```
$ ./browse look | grep -n -i -E "solcast|combobox|option" | head -30
```

```
Clicked f2e547.

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
... (50 more lines in actions.jsonl)
```

```
50:                      - generic [ref=f2e567]: Solcast PV Forecast Forecast Today
51:                    - button "Remove Solcast PV Forecast Forecast Today" [ref=f2e568] [cursor=pointer]
52:                  - 'combobox "Forecast: search entities or enter a value" [ref=f2e485]'
```

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
... (50 more lines in actions.jsonl)
```

Listbox not open; try typing.

```
$ ./browse type f2e485 Solcast | grep -n -i "option"
```

```
57:                    - option "Add all 2" [ref=f2e582] [cursor=pointer]
58:                    - option "Forecast Solcast PV Forecast Forecast Day 3 sensor.solcast_pv_forecast_forecast_day_3" [ref=f2e587] [cursor=pointer]:
63:                    - option "Forecast Solcast PV Forecast Forecast Tomorrow sensor.solcast_pv_forecast_forecast_tomorrow" [ref=f2e595] [cursor=pointer]:
```

```
$ ./browse click f2e582 | grep -n -i -E "solcast|option|error"
```

```
52:                      - generic [ref=f2e567]: Solcast PV Forecast Forecast Today
53:                    - button "Remove Solcast PV Forecast Forecast Today" [ref=f2e568] [cursor=pointer]
57:                      - generic [ref=f2e609]: Solcast PV Forecast Forecast Day 3
58:                    - button "Remove Solcast PV Forecast Forecast Day 3" [ref=f2e610] [cursor=pointer]
62:                      - generic [ref=f2e619]: Solcast PV Forecast Forecast Tomorrow
63:                    - button "Remove Solcast PV Forecast Forecast Tomorrow" [ref=f2e620] [cursor=pointer]
```

```
$ ./browse click f2e494
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e632]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e633]
    - generic [ref=f2e634]:
      - paragraph [ref=f2e636]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e639 | grep -n -i "solar"
```

```
65:          - button "Solar" [ref=f2e114] [cursor=pointer]
96:                          - generic: Solar
265:                      - generic: Solar
266:                      - generic: Solar
269:                        - generic "Solar" [ref=f2e644]:
270:                          - button "Solar" [ref=f2e645] [cursor=pointer]
283:                      - generic: Solar
```

```
$ ./browse done "Added Solar element connected to Inverter (DC), with forecast sensors Solcast PV Forecast Forecast Today, Tomorrow and Day 3. Created successfully and Solar now appears under Home."
```

```
Recorded. You can stop now.
```

I added a Solar element to the Home hub and connected it to the Inverter. Its forecast uses all three Solcast sensors: Forecast Today, Forecast Tomorrow and Forecast Day 3. HAEO showed "Created configuration for Solar", and Solar now appears under Home.

I left the Curtailment section alone.

Points where I hesitated or went off course:
- **Connection:** The form had Inverter pre-selected, so I kept it. That matches your panels feeding the inverter, and it's the DC connection rather than the Switchboard (AC) one.
- **Forecast picker:** After I picked the first sensor, the list closed and clicking the field again didn't reopen it. I typed "Solcast" to bring it back, then used "Add all 2" to add the other two.


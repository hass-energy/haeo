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

Inverter, DC is already selected, which fits. Next I'll open the forecast field.

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
... (241 more lines in actions.jsonl)
```


```
$ ./browse click f2e547
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
$ ./browse click f2e485 | grep -c option; ./browse look | grep -E 'option "' | head -40 | cut -c1-200
```

```
0
```

```
$ ./browse type f2e485 energy_production; ./browse look | grep -E 'option "' | cut -c1-230
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
... (235 more lines in actions.jsonl)
```

"Add all 31" matches the 31 sensors still to add, and all of them are Forecast.Solar sensors.

```
$ ./browse click f2e814 | grep -vE 'option|img|generic \[ref=f2e[0-9]+\]: (East|North|South|West)' | tail -40
```

```
                    - generic [ref=f2e1264]:
                    - button "Remove South solar prediction forecast Estimated energy production - day after tomorrow" [ref=f2e1270] [cursor=pointer]
                  - generic [ref=f2e1273]:
                    - generic [ref=f2e1274]:
                    - button "Remove South solar prediction forecast Estimated energy production - today" [ref=f2e1279] [cursor=pointer]
                  - generic [ref=f2e1282]:
                    - generic [ref=f2e1283]:
                    - button "Remove South solar prediction forecast Estimated energy production - tomorrow" [ref=f2e1289] [cursor=pointer]
                  - generic [ref=f2e1292]:
                    - generic [ref=f2e1293]:
                    - button "Remove West solar production forecast Estimated energy production - 3 days from now" [ref=f2e1299] [cursor=pointer]
                  - generic [ref=f2e1302]:
... (28 more lines in actions.jsonl)
```

```
$ ./browse click f2e494 | head -60
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1380]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1381]
    - generic [ref=f2e1382]:
      - paragraph [ref=f2e1384]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e1387 | grep -i -m5 solar; ./browse done "Added Solar (connected to Inverter, DC) with all 32 Forecast.Solar sensors (east/north/south/west x today, tomorrow, day after, d3-d7)."
```

```
          - button "Solar" [ref=f2e114] [cursor=pointer]
                          - generic: Solar
                      - generic: Solar
                      - generic: Solar
                        - generic "Solar" [ref=f2e1392]:
Recorded. You can stop now.
```

I added a Solar element to HAEO. It connects to the Inverter (DC) and uses all 32 Forecast.Solar sensors. That is east, north, south and west, each with today, tomorrow, the day after tomorrow, and 3 to 7 days from now. HAEO showed "Created configuration for Solar", and Solar now appears under the Home hub.

I didn't open the new Solar element afterwards to re-read its saved sensor list. Before submitting, the field listed all 32 sensors, and the combined forecast preview showed a peak of 17.9 kW.

Points where I hesitated or was unsure:
- **Connection:** I kept the default "Inverter, DC" instead of "Switchboard, AC". I judged it right because the panels feed the inverter, but I didn't check it beyond that.
- **Sensor list:** I used "Add all 31" after picking the first sensor by hand, which assumes the search for "energy_production" matched only Forecast.Solar sensors. The listed names were all the four directions with the expected day suffixes, so I think it did.
- **Curtailment:** I left that section alone.


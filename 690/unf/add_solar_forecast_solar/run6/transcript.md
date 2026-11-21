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

Inverter connection is already selected. Open the forecast picker.

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
$ ./browse click f2e799 | grep -v "option \"Forecast" | head -80
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

Added. Submit.

```
$ ./browse click f2e494 | grep -c "Remove "; ./browse look | head -40
```

```
0
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
$ ./browse click f2e1132 | grep -i -m3 solar
```

```
$ ./browse done "Added Solar element (Inverter connection) with all 32 Forecast.Solar energy production sensors (east/north/south/west x 8 days)."
```

```
          - button "Solar" [ref=f2e114] [cursor=pointer]
                          - generic: Solar
                      - generic: Solar
```

```
Recorded. You can stop now.
```

I added a Solar element to HAEO. It uses all 32 Forecast.Solar estimated energy production sensors: east, north, south and west, for each of the 8 days (today, tomorrow, day after tomorrow, and 3 to 7 days from now). HAEO confirmed "Created configuration for Solar", and Solar now appears under Home.

I didn't reopen the Solar element to check the saved sensor list, so the 32 rests on the "Add all 32" count and the confirmation message.

I left the connection at its default, Inverter (DC), since the panels feed into your inverter.

Points where I hesitated or was unsure:
- **Sensor selection:** The picker's "Add all" button first offered 38 sensors, which included unrelated Sigen Plant sensors. I typed "energy_production" into the search box first, so "Add all" then covered only the 32 Forecast.Solar sensors.
- **Connection default:** I accepted the default without trying the other option, Switchboard (AC).
- **Optional sections:** I didn't open the Curtailment section.


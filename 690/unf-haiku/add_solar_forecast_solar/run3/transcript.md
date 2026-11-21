# Transcript


*Show current browser page accessibility tree*
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


*Click Solar to add a solar element*
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


*Open the forecast entity picker*
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


*Filter the forecast picker to Forecast.Solar sensors*
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


*Add all 32 filtered Forecast.Solar sensors*
```
$ ./browse click f2e799
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
... (205 more lines in actions.jsonl)
```


All 32 Forecast.Solar sensors are in the list (4 directions × today, tomorrow, day after tomorrow, and 3–7 days out). Submitting.

*Submit the solar configuration*
```
$ ./browse click f2e494
```

```
Clicked f2e494.

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
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e1132
```

```
Clicked f2e1132.

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


I added a Solar element to HAEO's Home hub with all 32 Forecast.Solar production sensors, and the Solar device now shows up under Home.

- **Connection:** I left it at "Inverter, DC", the default. You said the panels feed the inverter, so I took that as DC-coupled behind the inverter.
- **Forecast sensors:** I typed "energy_production" in the forecast picker, which narrowed it to exactly 32 entries (East, North, South and West, each with today, tomorrow, day after tomorrow, and 3 to 7 days out). I used "Add all 32" on that filtered list. The unfiltered "Add all" would have pulled in Sigen inverter sensors too.
- **Name:** "Solar" (the default).
- **Curtailment:** left at its default, which I did not change or review.
- **Result:** The success dialog said "Created configuration for Solar." The forecast preview shows about 17.9 kW peak over the next 168 hours. The Home hub now reports 7 devices and 60 entities.

Points where I hesitated or was unsure:
- I did not verify the Connection choice against your wiring. "Inverter, DC" is my reading of "feeds into your inverter," and it would be wrong if the panels are AC-coupled to the switchboard.
- The "Add all" button's count (38) was larger than the Forecast.Solar set. I only noticed that after reading the full list, so I had to filter first. A mistake there would have added Sigen sensors that are not solar forecasts.
- I did not open the Curtailment section, so I don't know whether it needs a setting for your installation.
- I did not check the new Solar entities' states or the optimizer output after submitting. I only confirmed that the configuration was created.


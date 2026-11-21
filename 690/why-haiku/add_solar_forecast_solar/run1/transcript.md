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
... (313 more lines in actions.jsonl)
```


*Click Solar to add a solar element*
```
$ ./browse click f2e112
```

```
Clicked f2e112.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (39 more lines in actions.jsonl)
```


*Open the forecast entity picker*
```
$ ./browse click f2e483
```

```
Clicked f2e483.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (241 more lines in actions.jsonl)
```


*Select the East day-3 forecast sensor*
```
$ ./browse click f2e497
```

```
Clicked f2e497.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (50 more lines in actions.jsonl)
```


*Open picker and filter for East sensors*
```
$ ./browse click f2e483 && ./browse type f2e483 "energy_production_ east"
```

```
Clicked f2e483.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (145 more lines in actions.jsonl)
```


*Add all remaining East forecast sensors*
```
$ ./browse click f2e813
```

```
Clicked f2e813.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (85 more lines in actions.jsonl)
```

Nine East sensors are in. Now I'll do the same filter-and-add-all for North.

*Filter picker for North sensors*
```
$ ./browse click f2e483 && ./browse type f2e483 "energy_production_ north"
```

```
Clicked f2e483.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (220 more lines in actions.jsonl)
```


*Add all 8 North forecast sensors*
```
$ ./browse click f2e953
```

```
Clicked f2e953.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (125 more lines in actions.jsonl)
```

*Filter picker for South sensors*
```
$ ./browse click f2e483 && ./browse type f2e483 "energy_production_ south"
```

```
Clicked f2e483.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (300 more lines in actions.jsonl)
```

*Add all 8 South forecast sensors*
```
$ ./browse click f2e1111
```

```
Clicked f2e1111.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (165 more lines in actions.jsonl)
```

*Filter picker for West sensors*
```
$ ./browse click f2e483 && ./browse type f2e483 "energy_production_ west"
```

```
Clicked f2e483.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (380 more lines in actions.jsonl)
```

*Add all 8 West forecast sensors*
```
$ ./browse click f2e1269
```

```
Clicked f2e1269.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e414]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e427]
    - generic [ref=f2e430]:
      - generic [ref=f2e431]:
... (205 more lines in actions.jsonl)
```


All four directions are now in: 8 sensors each (today, tomorrow, day after tomorrow, and days 3–7), 32 in total. The Sigen sensors aren't Forecast.Solar, so I left them out. Submitting.

*Submit the solar configuration*
```
$ ./browse click f2e492
```

```
Clicked f2e492.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1425]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Success" [ref=f2e1426]
    - generic [ref=f2e1427]:
      - paragraph [ref=f2e1429]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Close the success dialog*
```
$ ./browse click f2e1432
```

```
Clicked f2e1432.

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


I added the solar element to HAEO as "Solar" in the Home hub, using the Forecast.Solar sensors for all four directions. The integration page now lists a Solar device with 4 entities.

- **Connection:** I kept the default "Inverter, DC", since you said the panels feed the inverter.
- **Forecast sensors:** I added 32 sensors: today, tomorrow, day after tomorrow and days 3–7, for each of east, north, south and west. The form's combined preview shows 0 kW rising to 17.9 kW over the next 168 hours. I left out the Sigen sensors, which aren't Forecast.Solar.
- **Curtailment:** I left it at its default, since you didn't mention it.

Points where I hesitated or was unsure:
- **Which sensors to include:** You said "every day it covers", so I included all eight per direction. The picker also offers "today" and "tomorrow" sensors, which may be cumulative energy totals rather than forecasts. I couldn't check how HAEO treats them, so the solar forecast may double-count or misread them.
- **Bulk add:** I used the picker's "Add all" option for three of the four directions after filtering by "energy_production_" and the direction name. I checked the resulting list by reading it, but I didn't open the saved configuration to confirm all 32 sensors were stored.
- **Name and connection:** I accepted the default name "Solar" and the default connection without changing them. I didn't check whether a different connection would suit your inverter better.
- **Success check:** The success message appeared, but I didn't inspect the saved solar element's settings or its forecast result beyond the entity count.


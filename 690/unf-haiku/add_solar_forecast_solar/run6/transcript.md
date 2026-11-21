# Transcript


*Show current HAEO page*
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


*Click Solar element type button*
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


*Open forecast entity picker*
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
... (242 more lines in actions.jsonl)
```


*Filter forecast picker to energy production sensors*
```
$ ./browse type f2e483 "energy_production"
```

```
Typed into f2e483.

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
... (202 more lines in actions.jsonl)
```


*Click Add all 32 forecast sensors*
```
$ ./browse click f2e797
```

```
Clicked f2e797.

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


*Submit solar configuration*
```
$ ./browse click f2e492
```

```
Clicked f2e492.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1123]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Success" [ref=f2e1124]
    - generic [ref=f2e1125]:
      - paragraph [ref=f2e1127]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e1130
```

```
Clicked f2e1130.

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


I added the solar element to the Home hub as "Solar", using all 32 Forecast.Solar energy production sensors. HAEO confirmed "Created configuration for Solar", and a Solar device with 4 entities now appears under the hub.

Settings:
- **Name:** Solar (default).
- **Connection:** Inverter, DC (default), since the panels feed the inverter.
- **Forecast:** East, North, South and West, each with today, tomorrow, day after tomorrow and days 3 to 7 ahead. I filtered the picker to `energy_production` and used "Add all 32". The unfiltered "Add all 38" would also have pulled in Sigen plant sensors.
- **Curtailment:** left at its default.

Points where I hesitated or was unsure:
- **Connection choice:** I read "feeds into your inverter" as DC-coupled to the inverter, not AC at the switchboard. If the panels actually feed a separate AC inverter, this should be Switchboard instead.
- **Sensor scope:** I took "every day it covers" to mean all 8 sensors per direction, which made 32 in total. I did not check whether the "today" sensors are partial-day totals that HAEO handles differently. The combined preview on the form showed 0 kW now and up to 17.9 kW over 168 hours, which looked plausible, but I did not verify the numbers against your inverter.
- **Naming:** The South sensors are labelled "solar prediction forecast" while the others say "solar production forecast". I added them all anyway, since the request was for all of them.
- **Curtailment:** I didn't touch it because you didn't mention it, though it may matter if your inverter limits export.
- **Verification:** I confirmed creation through the success dialog and the device entity count. I did not open the new Solar element to check its saved forecast list.


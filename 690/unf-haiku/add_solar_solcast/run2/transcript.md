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


The solar panels feed the inverter, so the default "Inverter, DC" connection is right. Next I'll look for the Solcast forecast sensors.

*Open forecast picker and search for solcast*
```
$ ./browse click f2e485 && ./browse type f2e485 "solcast"
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
... (161 more lines in actions.jsonl)
```


The three Solcast forecast sensors are listed, and "Add all 3" adds exactly today, tomorrow and day 3. I'll use that.

*Click Add all 3 to add the Solcast forecast sensors*
```
$ ./browse click f2e562
```

```
Clicked f2e562.

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
... (60 more lines in actions.jsonl)
```


All three Solcast sensors are attached, and the combined forecast preview looks sensible. I'll leave the name as "Solar" and the curtailment section at its defaults, then submit.

*Submit the solar configuration*
```
$ ./browse click f2e494
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e601]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e602]
    - generic [ref=f2e603]:
      - paragraph [ref=f2e605]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e608
```

```
Clicked f2e608.

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


*Report that the solar element was created*
```
$ ./browse done "Added a Solar element to the Home hub: connection left at Inverter (DC), since the panels feed the inverter; name left as Solar; forecast set to the three Solcast PV sensors (Today, Tomorrow, Day 3) via Add all 3; curtailment left at default. Submitted and got 'Created configuration for Solar'. The Home hub now shows a Solar device with 4 entities."
```

```
Recorded. You can stop now.
```

I added the rooftop solar to the Home hub as "Solar" and HAEO confirmed "Created configuration for Solar". The Home hub now shows a Solar device with 4 entities.

- **Connection:** left at "Inverter, DC", since the panels feed the inverter.
- **Forecast:** the three Solcast sensors (Forecast Today, Forecast Tomorrow, Forecast Day 3) are attached. The combined preview shows about 23.2 kW at peak over 72 hours.
- **Name and curtailment:** left at the defaults.

Points where I hesitated or was unsure:

1. **"Add all 3" versus picking one by one:** I used "Add all 3" because the search showed exactly the three Solcast forecast sensors. I did not check that no other Solcast sensors were hidden by the search filter.
2. **Connection choice:** I was unsure whether "Inverter, DC" or "Switchboard, AC" was right. I chose DC because you said the panels feed the inverter, and the default was already set to it.
3. **Name:** I kept "Solar" rather than something like "Rooftop Solar". It is a cosmetic choice I did not confirm with you.
4. **Curtailment:** I left it at the default without reading what it does. I did not open it, so I do not know whether it needs configuring for your setup.
5. **Verification:** I confirmed success from the dialog and the new device entry. I did not reopen the Solar element to check that the three forecast sensors were saved.


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


*Click the Solar element button*
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

*Search forecast picker for solcast entities*
```
$ ./browse type f2e483 solcast
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
... (92 more lines in actions.jsonl)
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
... (57 more lines in actions.jsonl)
```


*Add all three Solcast forecast sensors*
```
$ ./browse click f2e560
```

```
Clicked f2e560.

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
... (60 more lines in actions.jsonl)
```


*Submit the solar configuration*
```
$ ./browse click f2e492
```

```
Clicked f2e492.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e599]:
  - generic [ref=f2e415]:
    - banner [ref=f2e417]:
      - generic [ref=f2e418]:
        - generic "Close" [ref=f2e421]:
          - button "Close" [ref=f2e422] [cursor=pointer]
        - generic "Success" [ref=f2e600]
    - generic [ref=f2e601]:
      - paragraph [ref=f2e603]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Finish the success dialog*
```
$ ./browse click f2e606
```

```
Clicked f2e606.

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
$ ./browse done "Added a Solar element named 'Solar' to the Home hub. Connection is 'Inverter, DC' since the panels feed the inverter. Forecast uses all three Solcast PV Forecast sensors (Today, Tomorrow, Day 3). The configuration was created, and the Solar device now appears under the Home hub with 4 entities."
```

```
Recorded. You can stop now.
```

I added the Solar element to the Home hub and it was created. The Solar device now appears under Home with 4 entities.

- **Name:** left as the default, "Solar".
- **Connection:** "Inverter, DC", which is the default. Your panels feed the inverter, so I kept this rather than "Switchboard, AC".
- **Forecast:** I used "Add all 3" to add the Solcast sensors for Today, Tomorrow and Day 3. The forecast preview showed a combined curve reaching about 23.2 kW.
- **Curtailment:** left unconfigured.

Points where I hesitated or might have gone wrong:

1. **Connection choice:** I chose "Inverter, DC" from the panels' physical wiring. I did not check how HAEO's model uses the two options, so if your inverter is actually on the AC side, this would need changing.
2. **Name:** I kept "Solar" without thinking about whether a more specific name would help if you add more arrays later.
3. **Curtailment:** I skipped this section without reading its help text. It is probably optional, but I did not confirm that.
4. **Forecast entities:** I picked all three Solcast sensors, as you asked, but did not check whether HAEO expects one combined forecast or accepts several.
5. **Verification:** I confirmed the Solar device exists, but I did not open its entities to check the values.


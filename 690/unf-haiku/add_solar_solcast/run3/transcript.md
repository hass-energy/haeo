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


*Open forecast picker and search for Solcast*
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

"Add all 3" adds exactly the three Solcast sensors (today, tomorrow, day 3), so I'll use that.

*Click Add all 3 for Solcast forecast sensors*
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


The three Solcast sensors are attached, and the connection is Inverter (DC), which matches panels feeding the inverter. I'll leave Curtailment at its default and submit.

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


*Report that the solar element was added*
```
$ ./browse done "Added a Solar element to the Home hub: connection set to Inverter (DC), since the panels feed the inverter. Forecast set to the three Solcast PV sensors (Forecast Today, Forecast Tomorrow, Forecast Day 3). Name left as the default 'Solar'. HAEO now shows a Solar device with 4 entities and the success dialog said 'Created configuration for Solar'."
```

```
Recorded. You can stop now.
```

The Solar element is added to the Home hub. It uses the Inverter (DC) connection and the three Solcast PV forecast sensors. HAEO reports "Created configuration for Solar", and the Home hub now shows a Solar device with 4 entities. I didn't reopen the element to confirm the saved forecast values.

Points where I hesitated or was unsure:

1. **Connection choice:** The form offered "Inverter, DC" and "Switchboard, AC". I picked Inverter because you said the panels feed the inverter. I kept the default rather than checking how HAEO's energy flows are modelled, since I can't read its docs.
2. **Forecast sensors:** The picker offered "Add all 3", and I used it. Its list also showed unrelated sensors such as the Sigen plant power readings. I picked only the Solcast entries, which are Forecast Today, Forecast Tomorrow and Forecast Day 3. I didn't check whether Solcast also provides other PV sensors that should be included.
3. **Name:** I left the name as the default "Solar". You didn't ask for a specific name, so this is a guess.
4. **Curtailment:** This section was collapsed and I left it at its default. I didn't open it to see what it offers, so I don't know whether any curtailment setting should apply to your panels.
5. **Verification:** I didn't reopen the saved Solar configuration to check the stored connection and forecast values. I relied on the success message and the new entity count.


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
... (350 more lines in actions.jsonl)
```


The pool pump runs continuously at a fixed draw, so it fits the plain "Load" type rather than "Deferrable load". I'll open the Load form.

*Click the Load element type button*
```
$ ./browse click f2e108
```

```
Clicked f2e108.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Load configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (47 more lines in actions.jsonl)
```


The form is open. I'll set the name, then look at the Forecast field to see what units it expects.

*Enter Pool pump as the load name*
```
$ ./browse type f2e490 "Pool pump"
```

```
Typed into f2e490.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Load configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (47 more lines in actions.jsonl)
```

*Focus the Forecast field to see its options*
```
$ ./browse click f2e534
```

```
Clicked f2e534.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Load configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (250 more lines in actions.jsonl)
```


The dropdown lists power sensors in kW, and it accepts a typed value. I'll enter 0.8 as a constant.

*Type constant 0.8 into the Forecast field*
```
$ ./browse type f2e534 "0.8"
```

```
Typed into f2e534.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Load configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (54 more lines in actions.jsonl)
```

*Select the Fixed value 0.8 kW option*
```
$ ./browse click f2e849
```

```
Clicked f2e849.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Load configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (55 more lines in actions.jsonl)
```


The constant 0.8 kW is set, and Switchboard (AC) is the default connection, which fits a pool pump. I'll submit.

*Submit the Pool pump load configuration*
```
$ ./browse click f2e543
```

```
Clicked f2e543.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e864]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e865]
    - generic [ref=f2e866]:
      - paragraph [ref=f2e868]: Created configuration for Pool pump.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e871
```

```
Clicked f2e871.

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
... (390 more lines in actions.jsonl)
```


*Report that the pool pump load was added*
```
$ ./browse done "Added 'Pool pump' as a Load under the Home hub. Connection: Switchboard (AC), the default. Forecast: fixed value 0.8 kW, so it is a constant draw. Shedding left at its default. The Home hub now lists a Pool pump load device with 12 entities."
```

```
Recorded. You can stop now.
```

I added "Pool pump" as a Load under the Home hub, with a fixed 0.8 kW forecast. The Home hub now lists a Pool pump device with 12 entities, next to the existing Load.

Where I hesitated or was unsure:

- **Load vs. Deferrable load:** I chose plain Load because the pump runs continuously at a steady draw and can't be scheduled. A deferrable load would only fit if the pump could be shifted to other times.
- **Connection:** I left the default "Switchboard, AC". I assumed the pump is on the AC side of the house, since I didn't check which circuit it is wired to. If it sits behind the inverter, this would need to change to Inverter, DC.
- **Units:** The Forecast picker lists power sensors in kW and offered "Fixed value 0.8 kW" after I typed 0.8. I took that as confirmation that 0.8 means kW, not W.
- **Shedding:** I left this section at its default. I didn't check whether the pump should be allowed to shed, since you didn't mention it.
- **Verification:** I confirmed the device and entity counts changed, but I didn't open the new Pool pump entities to check their values.


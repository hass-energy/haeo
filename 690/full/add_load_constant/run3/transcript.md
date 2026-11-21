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
... (350 more lines in actions.jsonl)
```

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

Switchboard AC is default and fits a pool pump. Set name and forecast.

```
$ ./browse type f2e490 "Pool pump"; ./browse type f2e534 0.8
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
... (113 more lines in actions.jsonl)
```

```
$ ./browse click f2e548
```

```
Clicked f2e548.

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

```
$ ./browse click f2e543
```

```
Clicked f2e543.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e563]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e564]
    - generic [ref=f2e565]:
      - paragraph [ref=f2e567]: Created configuration for Pool pump.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e570 >/dev/null; ./browse look | grep -n "Pool pump"
```

```
263:                      - generic: Pool pump
281:                      - generic: Pool pump
```

```
$ ./browse done "Added a Load named 'Pool pump' connected to the Switchboard (AC) with a fixed forecast of 0.8 kW. It now appears under the Home hub."
```

```
Recorded. You can stop now.
```

I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW forecast, connected to the Switchboard. HAEO showed "Created configuration for Pool pump", and the name now appears in the hub's list.

Points where I hesitated or made assumptions:
- **Connection:** I kept the default, Switchboard (AC), without checking it against your wiring. I assumed a pool pump is an ordinary mains load, like the existing "Load". If it hangs off the inverter instead, the connection needs changing.
- **Forecast field:** It asks for a forecast, and I typed 0.8 so it offered "Fixed value 0.8 kW", which I picked. That fits "runs all the time", but I didn't confirm that a fixed value is treated as constant over time.
- **Shedding:** I didn't open or change the optional "Shedding" section, so it keeps its defaults.


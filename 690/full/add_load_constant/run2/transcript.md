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

Switchboard AC is already selected, which suits a pool pump. Next I'll set the name and the forecast value.

```
$ ./browse type f2e490 "Pool pump"; ./browse type f2e534 "0.8"
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
$ ./browse click f2e570 | grep -i -m5 "pool"
```

```
                      - generic: Pool pump
                      - generic: Pool pump
```

```
$ ./browse done "Added a Load named 'Pool pump' on the Switchboard (AC) with a fixed 0.8 kW forecast. It now appears under the Home hub."
```

```
Recorded. You can stop now.
```

"Pool pump" is now a load in your Home hub. It's set to a fixed 0.8 kW and connected to the Switchboard (AC), and it shows in the hub's device list. HAEO confirmed with "Created configuration for Pool pump."

Points where I hesitated or assumed something:
- **Connection:** I kept the pre-selected Switchboard (AC) connection without checking it against your wiring. I assumed a pool pump is an AC load.
- **Shedding:** I left the "Shedding" section untouched, since the pump runs all the time. I didn't open it to check what it does.
- **Fixed value entry:** The forecast box offered a "Fixed value 0.8 kW" option when I typed 0.8. I assumed that was the right way to enter a constant, and it was the only fixed-value option offered.


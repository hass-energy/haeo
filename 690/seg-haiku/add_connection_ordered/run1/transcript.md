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
... (362 more lines in actions.jsonl)
```


*Click Connection element button to add*
```
$ ./browse click f2e126
```

```
Clicked f2e126.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (22 more lines in actions.jsonl)
```


*Click Add a segment button*
```
$ ./browse click f2e516
```

```
Clicked f2e516.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (26 more lines in actions.jsonl)
```


*Add Efficiency segment first*
```
$ ./browse click f2e534
```

```
Clicked f2e534.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (34 more lines in actions.jsonl)
```


*Focus the efficiency field*
```
$ ./browse click f2e563
```

```
Clicked f2e563.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (43 more lines in actions.jsonl)
```


*Enter 96 as efficiency value*
```
$ ./browse type f2e563 "96"
```

```
Typed into f2e563.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (41 more lines in actions.jsonl)
```

The picker offers "Fixed value 96 %". I'll select it.

*Select fixed value 96 percent*
```
$ ./browse click f2e580
```

```
Clicked f2e580.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (42 more lines in actions.jsonl)
```


Efficiency is set to 96%. Next I'll add the 8 kW limit after it so the cap applies to power arriving at the switchboard.

*Add a segment after efficiency*
```
$ ./browse click f2e566
```

```
Clicked f2e566.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (46 more lines in actions.jsonl)
```

*Choose Limit segment type*
```
$ ./browse click f2e595
```

```
Clicked f2e595.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (54 more lines in actions.jsonl)
```


*Enter 8 as limit value*
```
$ ./browse type f2e630 "8"
```

```
Typed into f2e630.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (61 more lines in actions.jsonl)
```

*Select fixed value 8 kW*
```
$ ./browse click f2e639
```

```
Clicked f2e639.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (62 more lines in actions.jsonl)
```


Both segments are set. I'll give the connection a descriptive name instead of the default "Connection".

*Rename connection to describe the transformer*
```
$ ./browse type f2e505 "Inverter to Switchboard transformer"
```

```
Typed into f2e505.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e491]
    - generic [ref=f2e494]:
      - generic [ref=f2e495]:
... (62 more lines in actions.jsonl)
```


The form now reads: Inverter → Efficiency 96% → Limit 8 kW → Switchboard. Submitting.

*Submit the connection form*
```
$ ./browse click f2e525
```

```
Clicked f2e525.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e654]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e655]
    - generic [ref=f2e656]:
      - paragraph [ref=f2e658]: Created configuration for Inverter to Switchboard transformer.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e661
```

```
Clicked f2e661.

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
... (402 more lines in actions.jsonl)
```


I added the connection "Inverter to Switchboard transformer" to the Home hub. It runs from Inverter to Switchboard with two segments in this order:

1. **Efficiency: fixed 96%** (the transformer keeps 96% and loses 4%)
2. **Limit: fixed 8 kW** (the fuse cap on what reaches the switchboard)

The success dialog confirmed creation, and the hub list now shows the connection with 3 entities.

Points where I hesitated, were unsure, or could have gone wrong:

- **Segment order:** I put Efficiency before Limit so that the 8 kW cap applies to power after the 4% loss, which is what the fuse sees. I inferred that from the "applied in order" wording rather than from documentation, so I did not verify how the optimizer actually applies it.
- **Efficiency units:** The field offered "Fixed value 96 %" when I typed 96, and I picked that rather than 0.96. The UI displayed it as a percentage, so I believe it is right, but I did not check the stored value.
- **Limit meaning:** I assumed the 8 kW limit caps instantaneous power through the connection. I did not confirm that it is not an energy or per-interval limit.
- **Connection name:** The default was "Connection". I renamed it to "Inverter to Switchboard transformer" for clarity. That was my choice, not something you asked for.
- **Direction:** The help text says the connection is one-way. I left the default direction, so power can flow only from Inverter to Switchboard, which matches your setup.
- **Not re-checked:** I did not reopen the saved connection to confirm the segments and values persisted as entered.


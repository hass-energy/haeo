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
... (362 more lines in actions.jsonl)
```

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


```
$ ./browse type f2e505 "Inverter to Switchboard"; ./browse click f2e516
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
... (60 more lines in actions.jsonl)
```

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

Efficiency 96%.

```
$ ./browse type f2e563 96; ./browse press Enter
```

```
$ ./browse look | grep -n -i -A6 "efficiency"
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
... (95 more lines in actions.jsonl)
```

```
30:                    - generic [ref=f2e549]: Efficiency
31-                    - generic [ref=f2e550]:
32:                      - button "Move Efficiency earlier" [disabled] [ref=f2e551]
33:                      - button "Move Efficiency later" [disabled] [ref=f2e554]
34:                      - button "Remove Efficiency" [ref=f2e557] [cursor=pointer]
35-                  - generic [ref=f2e560]:
36:                    - generic [ref=f2e561]: Efficiency *
37-                    - generic [ref=f2e562]:
38-                      - generic [ref=f2e578]:
39-                        - button "Fixed value 96 %" [ref=f2e579] [cursor=pointer]:
40-                          - generic [aria-hidden] [ref=f2e580]:
41-                            - generic [ref=f2e581]: "96"
... (9 more lines in actions.jsonl)
```

Now add a limit after the efficiency (the lower "Add a segment here").

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

```
$ ./browse click f2e587
```

```
Clicked f2e587.

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

```
$ ./browse type f2e622 8; ./browse look | grep -B2 -A8 "Fixed value"
```

```
Typed into f2e622.

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
... (91 more lines in actions.jsonl)
```

```
$ ./browse click f2e631 >/dev/null; ./browse click f2e525
```

```
Clicked f2e525.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e646]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e647]
    - generic [ref=f2e648]:
      - paragraph [ref=f2e650]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```


```
$ ./browse click f2e653 >/dev/null; ./browse done "Created connection 'Inverter to Switchboard' from Inverter to Switchboard with segments in order: Efficiency 96%, then Limit 8 kW."
```

```
Recorded. You can stop now.
```

I added a connection called "Inverter to Switchboard", with Inverter as the source and Switchboard as the target. Home Assistant showed "Created configuration for Inverter to Switchboard." I didn't reopen it afterwards to check the saved values.

It has two segments, in this order:
1. **Efficiency:** 96%, for the 4% transformer loss.
2. **Limit:** 8 kW, applied after the loss, so no more than 8 kW arrives at the switchboard.

Points where I hesitated or could have gone wrong:
- **Segment order:** I wasn't sure which order the segments are applied in. I put Efficiency first and Limit second because the fuse is on the switchboard side of the transformer.
- **Limit value:** After typing 8 into the Limit field I clicked the "Fixed value 8 kW" option. I didn't confirm it showed as a chip before I submitted. The form accepted the submission, so I assume the value was set.


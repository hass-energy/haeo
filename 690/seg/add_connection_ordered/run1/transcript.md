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

Source/target already correct. Add segments.

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

Add the limit after the efficiency (the lower "add" button).

```
$ ./browse type f2e563 96; ./browse click f2e566
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
... (87 more lines in actions.jsonl)
```


```
$ ./browse type f2e563 96; ./browse click f2e572
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
... (94 more lines in actions.jsonl)
```

Ref was stale; click the new one.

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


```
$ ./browse type f2e630 8
```

```
$ ./browse look | grep -n -A8 listbox
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

```
58:                    - listbox [ref=f2e637]:
59-                      - group [ref=f2e638]:
60-                        - option "Fixed value 8 kW" [ref=f2e639] [cursor=pointer]:
61-                          - generic [aria-hidden] [ref=f2e640]:
62-                            - generic [ref=f2e641]: "8"
63-                            - generic [ref=f2e642]: kW
64-                          - generic [ref=f2e643]: Fixed value
65-                - button "Add a segment here" [ref=f2e633] [cursor=pointer]
66-              - generic [ref=f2e520]:
```


```
$ ./browse click f2e639 >/dev/null; ./browse type f2e505 "Inverter to Switchboard" | grep -E "Fixed value|textbox|Limit|Submit"
```

```
            - textbox "Connection name*" [ref=f2e505]:
                        - button "Fixed value 96 %" [ref=f2e587] [cursor=pointer]:
                          - generic [ref=f2e591]: Fixed value
                    - generic [ref=f2e616]: Limit
                      - button "Move Limit earlier" [ref=f2e618] [cursor=pointer]
                      - button "Move Limit later" [disabled] [ref=f2e621]
                      - button "Remove Limit" [ref=f2e624] [cursor=pointer]
                    - generic [ref=f2e628]: Limit *
                        - button "Fixed value 8 kW" [ref=f2e646] [cursor=pointer]:
                          - generic [ref=f2e650]: Fixed value
                      - 'combobox "Limit: search entities or enter a value" [ref=f2e630]'
      - button "Submit" [ref=f2e525] [cursor=pointer]
```

```
$ ./browse click f2e525 | head -30
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
      - paragraph [ref=f2e658]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e661 >/dev/null; ./browse done "Added connection 'Inverter to Switchboard' (Inverter -> Switchboard) with segments in order: Efficiency 96%, then Limit 8 kW, so the 8 kW cap applies after the 4% loss, at the switchboard side."
```

```
Recorded. You can stop now.
```

I added a connection called "Inverter to Switchboard", running from the Inverter to the Switchboard. Home Assistant confirmed it was created, but I didn't reopen it afterwards to check the saved values.

It has two segments, in this order:
1. **Efficiency, 96%.** This models the transformer's 4% loss.
2. **Limit, 8 kW.** Because it comes after the efficiency segment, the 8 kW cap applies to the power that arrives at the switchboard, not the power leaving the inverter.

Points where I hesitated or made mistakes:
- **Efficiency value:** My first attempt at the 96 value didn't stick. Typing it only fills the search box, and I had to click the "Fixed value 96 %" option to commit it. I also used a stale option reference once and had to retry.
- **Segment order:** The form doesn't say which order is correct. I put efficiency first on my own reasoning that the fuse sits on the switchboard side, after the loss.
- **Limit direction:** The single Limit field doesn't say whether it caps one direction or both. The connection is one-way anyway, so I assumed it doesn't matter.


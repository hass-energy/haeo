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
      - generic [ref=f2e497]:
... (26 more lines in actions.jsonl)
```

Endpoints region looks empty; take a screenshot.

```
$ ./browse type f2e502 "Inverter to Switchboard"; ./browse screenshot
```

```
Typed into f2e502.

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
... (44 more lines in actions.jsonl)
```

Source Inverter and target Switchboard are already selected by default. Now max power.

```
$ ./browse type f2e526 10
```

```
Typed into f2e526.

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
... (50 more lines in actions.jsonl)
```

```
$ ./browse click f2e571
```

```
Clicked f2e571.

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
... (51 more lines in actions.jsonl)
```

```
$ ./browse click f2e551
```

```
Clicked f2e551.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e586]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e587]
    - generic [ref=f2e588]:
      - paragraph [ref=f2e590]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e593
```

```
$ ./browse done "Added connection 'Inverter to Switchboard' (source Inverter, target Switchboard) with max power 10 kW; success confirmed."
```

```
Clicked f2e593.

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

```
Recorded. You can stop now.
```

I added a connection named "Inverter to Switchboard" in HAEO. Its source is Inverter, its target is Switchboard, and its max power is 10 kW. After I submitted the form, HAEO showed "Created configuration for Inverter to Switchboard." The new connection also appears in the Home hub's device list with 2 entities. I didn't open it again to check that the 10 kW limit was saved.

Points where I hesitated or was unsure:
- **Endpoint defaults:** The Source and Target dropdowns were already set to Inverter and Switchboard, so I left them as they were. I only confirmed this from the page text. I didn't change them or look at the screenshot I took.
- **Max power field:** Typing "10" in the Max power box brought up a "Fixed value 10 kW" option, and I picked it. The field's unit wasn't labelled until that point, so I relied on the option showing kW.
- **Other settings:** I left Price empty and didn't open the Connection efficiency section, since you didn't ask for either.


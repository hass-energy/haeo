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

Source and target already right. Add a segment for the limit.

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
$ ./browse click f2e528
```

```
Clicked f2e528.

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

```
$ ./browse type f2e563 10; ./browse press Enter
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

Name it something clearer, then submit.

```
$ ./browse type f2e505 "Inverter to Switchboard"; ./browse click f2e525
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
... (55 more lines in actions.jsonl)
```

```
$ ./browse click f2e594
```

```
Clicked f2e594.

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
$ ./browse done "Added connection 'Inverter to Switchboard' from Inverter (source) to Switchboard (target) with a single Limit segment of fixed 10 kW; it now appears in the hub's device list."
```

```
Recorded. You can stop now.
```

I added a connection called "Inverter to Switchboard" in HAEO. It runs from the Inverter to the Switchboard with a fixed 10 kW limit. HAEO showed a success message, and the connection now appears in the Home hub's device list.

I didn't open the saved connection again to re-read the limit.

Points where I hesitated or deviated:
- **Connection name:** the form pre-filled "Connection". I renamed it to "Inverter to Switchboard" so it is easy to identify. You didn't ask for a name.
- **Source and target:** the form had already selected Inverter as the source and Switchboard as the target, so I left them as they were.
- **Limit entry:** the limit field offers entities or a typed value. I typed 10 and chose "Fixed value 10 kW" rather than picking a sensor.


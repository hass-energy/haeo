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

*Open Home hub configure*
```
$ ./browse click f2e159
```

```
Clicked f2e159.

Page: /config/integrations/integration/haeo
- alertdialog "HAEO settings" [ref=f2e478]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "HAEO settings" [ref=f2e491]
        - link [ref=f2e493] [cursor=pointer]:
          - /url: https://github.com/hass-energy/haeo
... (31 more lines in actions.jsonl)
```


The Configure button opened the hub settings, not what I need. I'll close it and use the "Connection" add button instead.

*Close HAEO settings dialog*
```
$ ./browse click f2e486
```

*Look at page after closing dialog*
```
$ ./browse look
```

```
Clicked f2e486.

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
... (364 more lines in actions.jsonl)
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

*Click Connection element add button*
```
$ ./browse click f2e126
```

```
Clicked f2e126.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (22 more lines in actions.jsonl)
```


The source is Inverter and the target is Switchboard, which is correct. The 10 kW limit probably goes in a segment, so I'll look at the "Add a segment here" control.

*Click Add a segment here*
```
$ ./browse click f2e589
```

```
Clicked f2e589.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (26 more lines in actions.jsonl)
```

*Choose Limit segment type*
```
$ ./browse click f2e601
```

```
Clicked f2e601.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (34 more lines in actions.jsonl)
```


The Limit segment has an entity-or-value field. I'll enter the value and check the unit it picks up.

*Type 10 into Limit field*
```
$ ./browse type f2e636 10
```

```
Typed into f2e636.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (41 more lines in actions.jsonl)
```

The picker offers "Fixed value 10 kW", which is the right option. I'll select it.

*Select Fixed value 10 kW option*
```
$ ./browse click f2e645
```

```
Clicked f2e645.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (42 more lines in actions.jsonl)
```


The 10 kW limit is set. The name still says the generic "Connection", so I'll rename it to make this link easy to identify later.

*Rename connection to Inverter to Switchboard*
```
$ ./browse type f2e578 "Inverter to Switchboard"
```

```
Typed into f2e578.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e551]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e564]
    - generic [ref=f2e567]:
      - generic [ref=f2e568]:
... (42 more lines in actions.jsonl)
```


Source is Inverter, target is Switchboard, and the limit is 10 kW. Submitting now.

*Submit connection configuration*
```
$ ./browse click f2e598
```

```
Clicked f2e598.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e660]:
  - generic [ref=f2e552]:
    - banner [ref=f2e554]:
      - generic [ref=f2e555]:
        - generic "Close" [ref=f2e558]:
          - button "Close" [ref=f2e559] [cursor=pointer]
        - generic "Success" [ref=f2e661]
    - generic [ref=f2e662]:
      - paragraph [ref=f2e664]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e667
```

```
Clicked f2e667.

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


The connection is set up: Inverter to Switchboard with a fixed 10 kW limit. HAEO now lists a new "Inverter to Switchboard" connection under Home, with 2 entities.

I did not reopen the saved connection to read the limit back. The limit was confirmed as "Fixed value 10 kW" in the form before I submitted, and the success message appeared.

Points where I hesitated or made a choice:
- **Wrong dialog first:** I clicked the hub's "Configure" button by mistake, which opened the Home hub settings. I closed it without changing anything and used the "Connection" add button instead.
- **Name:** You didn't ask for a name, so I renamed the default "Connection" to "Inverter to Switchboard" so it is easy to identify. It can be changed if you prefer another name.
- **Units:** The limit field took a bare "10" and offered it as "Fixed value 10 kW". I accepted that option rather than entering a unit myself.
- **Direction:** The connection is one-way, which matches the cable limit you described (inverter to switchboard). The form says power in the other direction needs a second connection with the endpoints swapped. I did not add one, because you only asked for this direction.


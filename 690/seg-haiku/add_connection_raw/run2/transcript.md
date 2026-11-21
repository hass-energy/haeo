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
... (362 more lines in actions.jsonl)
```

*Click Connection element type button*
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


The source is already Inverter and the target is Switchboard. The limit must be set through a segment, so I'll look at the segment options.

*Click Add a segment here button*
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

*Choose Limit segment type*
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


*Enter 10 in the Limit field*
```
$ ./browse type f2e563 10
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

The dropdown offers "Fixed value 10 kW", so I'll select it.

*Select Fixed value 10 kW option*
```
$ ./browse click f2e572
```

```
Clicked f2e572.

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


The limit is set to 10 kW. I'll give the connection a descriptive name in place of the default "Connection".

*Rename connection to Inverter to Switchboard*
```
$ ./browse type f2e505 "Inverter to Switchboard"
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
... (42 more lines in actions.jsonl)
```

*Submit the connection*
```
$ ./browse click f2e525
```

```
Clicked f2e525.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e587]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e588]
    - generic [ref=f2e589]:
      - paragraph [ref=f2e591]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
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

*Report task completion summary*
```
$ ./browse done "Added a Connection named 'Inverter to Switchboard' from Inverter (source) to Switchboard (target) with one Limit segment set to a fixed value of 10 kW. HAEO confirmed 'Created configuration for Inverter to Switchboard' and the Home hub now lists the new Connection device with 2 entities."
```

```
Recorded. You can stop now.
```

I added the connection. HAEO confirmed "Created configuration for Inverter to Switchboard", and the Home hub now lists an "Inverter to Switchboard" Connection device with 2 entities.

- **Source and target:** Inverter as the source and Switchboard as the target, which were already selected when the form opened.
- **Limit:** one Limit segment set to a fixed value of 10 kW, chosen from the "Fixed value 10 kW" suggestion. The form's Limit field takes entities or values, and the 10 kW suggestion was the only fixed value offered.
- **Name:** I renamed the connection from the default "Connection" to "Inverter to Switchboard". You didn't ask for a name, so change it if you prefer another.

Points where I hesitated or was unsure:
- I did not check the 10 kW limit against the live Connection entity's attributes afterwards, so I'm relying on the form and the success message to confirm the value.
- The connection is one-way, as the form's help text says. Power flowing back from the Switchboard to the Inverter is not limited by this connection. The help text suggests adding a second connection with the endpoints swapped if you need that, and I did not add one.
- I assumed the Limit field's units are kW because the dropdown labelled the value "10 kW". I did not confirm the unit independently.


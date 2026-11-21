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


*Click Connection button to add a connection*
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
... (43 more lines in actions.jsonl)
```


*Enter 10 into the Max power field*
```
$ ./browse click f2e541 && ./browse type f2e541 "10"
```

```
Clicked f2e541.

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
... (308 more lines in actions.jsonl)
```


*Select the Fixed value 10 kW option*
```
$ ./browse click f2e872
```

```
Clicked f2e872.

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
... (51 more lines in actions.jsonl)
```

*Submit the connection configuration*
```
$ ./browse click f2e566
```

```
Clicked f2e566.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e887]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e888]
    - generic [ref=f2e889]:
      - paragraph [ref=f2e891]: Created configuration for Inverter to Switchboard.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e894
```

```
Clicked f2e894.

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


I added the connection "Inverter to Switchboard" to the Home hub, with the source set to Inverter, the target to Switchboard, and the max power fixed at 10 kW. HAEO confirmed "Created configuration for Inverter to Switchboard," and the new Connection device appears under Home. I did not reopen it afterwards to re-check the saved value.

Points where I hesitated or was unsure:

- **Unit of the power limit:** The Max power field offered a "Fixed value 10 kW" option, so I picked that rather than typing a bare number. This matches the cable rating in kW.
- **Direction:** The form pre-filled Source as Inverter and Target as Switchboard, which is the direction you asked for. The help text says reverse flow needs a second connection, and I did not add one because you asked for only one.
- **Connection name:** I renamed the default "Connection" to "Inverter to Switchboard" for clarity. This was my own choice, not something you asked for.
- **Optional fields left blank:** I left Pricing and Connection efficiency empty because the task did not mention them. I did not check whether HAEO fills in defaults for them.
- **Verification:** I confirmed the 10 kW selection on screen before submitting, but I did not reopen the saved connection to confirm the stored value.


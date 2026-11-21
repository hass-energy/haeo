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


*Enter 10 in the Max power field*
```
$ ./browse type f2e541 "10"
```

```
Typed into f2e541.

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

The option offered is "Fixed value 10 kW", which is the right unit. Selecting it.

*Select the fixed value 10 kW option*
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


Max power is set to 10 kW, with Inverter as source and Switchboard as target. Submitting.

*Submit the connection form*
```
$ ./browse click f2e566
```

```
Clicked f2e566.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e586]:
  - generic [ref=f2e479]:
    - banner [ref=f2e481]:
      - generic [ref=f2e482]:
        - generic "Close" [ref=f2e485]:
          - button "Close" [ref=f2e486] [cursor=pointer]
        - generic "Success" [ref=f2e587]
    - generic [ref=f2e588]:
      - paragraph [ref=f2e590]: Created configuration for Connection.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e593
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


I added the connection from Inverter to Switchboard with a max power of 10 kW. HAEO confirmed "Created configuration for Connection", and the hub now lists a Connection device with 2 entities.

I did not reopen the new connection to check the saved value. The 10 kW limit was shown as a chip in the form before I submitted.

Points where I hesitated or was unsure:
- **Units:** The Max power field took a plain "10" and offered "Fixed value 10 kW" as the suggestion. I picked that option, so the value is 10 kW rather than 10 W.
- **Direction:** The form pre-filled Source as Inverter and Target as Switchboard, which matches "from the Inverter to the Switchboard". The form's help text says reverse flow needs a second connection, and I did not add one, since you only asked for this direction.
- **Name:** I left the default name "Connection", which is generic. Naming it something like "Inverter to Switchboard" would make it easier to tell apart if you add more connections later. That was my choice, not something you asked for.
- **Optional fields:** I left Price and Connection efficiency empty, since the task did not mention them.


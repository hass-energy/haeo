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
... (350 more lines in actions.jsonl)
```

The HAEO hub is listed, and there's a "Load" button under "Add hub"'s element-type buttons. I'll click "Load" to add a new load subentry to the Home hub.

*Click Load to add a load element*
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


The Load form has a name, a connection, and a Forecast field that accepts an entity or a typed value. I'll set the name first.

*Enter Pool pump as load name*
```
$ ./browse type f2e490 "Pool pump"
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
... (47 more lines in actions.jsonl)
```


The connection is already Switchboard, which is right for a pump on the house's AC side. Next I'll enter the constant 0.8 in the Forecast field.

*Enter 0.8 as the forecast value*
```
$ ./browse type f2e534 "0.8"
```

```
Typed into f2e534.

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
... (54 more lines in actions.jsonl)
```

The picker offers "Fixed value 0.8 kW" in the unit HAEO uses, so I'll select that option.

*Select Fixed value 0.8 kW option*
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


The forecast now holds the fixed 0.8 kW value. The Shedding section is collapsed, so I'll open it and read what it controls before submitting.

*Expand Shedding section to read options*
```
$ ./browse click f2e538
```

```
Clicked f2e538.

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
... (70 more lines in actions.jsonl)
```


Shedding is already set to Off, which fits a pump that runs continuously, so I'll leave the defaults and submit.

*Submit the Pool pump load*
```
$ ./browse click f2e543
```

```
Clicked f2e543.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e587]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e588]
    - generic [ref=f2e589]:
      - paragraph [ref=f2e591]: Created configuration for Pool pump.
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
... (390 more lines in actions.jsonl)
```


*Report task completion*
```
$ ./browse done "Added a Load element named 'Pool pump' to the Home hub. Connection is Switchboard (AC, the default), Forecast is a fixed value of 0.8 kW, and Shedding is left at Off. The success dialog confirmed 'Created configuration for Pool pump', and it now appears under Home with its own device and 12 entities."
```

```
Recorded. You can stop now.
```

I added "Pool pump" to the Home hub as a Load with a fixed 0.8 kW forecast. The success dialog said "Created configuration for Pool pump", and it now shows under Home with its own device and 12 entities. I did not reopen the element afterwards to confirm the stored value.

Settings:
- **Name:** Pool pump
- **Connection:** Switchboard (AC), the default. I kept it because the pump is a house AC load.
- **Forecast:** Fixed value 0.8 kW, picked from the suggestion list.
- **Shedding:** left at Off, so the optimizer cannot cut the pump. That matches "runs all the time", but it was my choice, not something you stated.

Points where I hesitated or was unsure:
- **Connection:** I assumed Switchboard without checking how your pump is wired. If it sits on the inverter's DC side, it should be Inverter instead.
- **Shedding:** I left it Off and did not ask whether you want the optimizer allowed to switch the pump off when that would save money.
- **Verification:** I confirmed creation but did not open the new element to check the stored 0.8 kW value.
- **Consumption cost:** the Shedding section also has a Consumption cost field, which I left blank because you did not mention one.


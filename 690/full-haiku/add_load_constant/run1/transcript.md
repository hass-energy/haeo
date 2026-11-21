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


*Click Load to add a new load to the Home hub*
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


*Set the load name to Pool pump*
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


*Open the Forecast field to see options*
```
$ ./browse click f2e534
```

```
Clicked f2e534.

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
... (250 more lines in actions.jsonl)
```


*Type constant 0.8 into the forecast field*
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

*Select the Fixed value 0.8 kW option*
```
$ ./browse click f2e849
```

```
Clicked f2e849.

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


*Expand the Shedding section to review its options*
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


The shedding default is already "Off", which fits a pump that runs continuously. I'll leave it and submit.

*Submit the Pool pump load configuration*
```
$ ./browse click f2e543
```

```
Clicked f2e543.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e888]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e889]
    - generic [ref=f2e890]:
      - paragraph [ref=f2e892]: Created configuration for Pool pump.
... (1 more lines in actions.jsonl)
```

*Click Finish to close the success dialog*
```
$ ./browse click f2e895
```

```
Clicked f2e895.

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


I added "Pool pump" to the Home hub as a load with a fixed 0.8 kW forecast. It now appears in the hub's device list as a Load device with 12 entities.

Settings used:
- **Name:** Pool pump
- **Connection:** Switchboard, AC (the default, which fits a pump on the house AC side)
- **Forecast:** Fixed value 0.8 kW, chosen from the picker's "Fixed value" option, so it is a constant rather than a sensor
- **Shedding:** "Allow shedding" left at Off (the default), since the pump runs all the time
- **Consumption cost:** left empty

I did not open the new entities to confirm the 0.8 kW value, so that check rests on the form and the success message.

Points where I hesitated or was unsure:
- **Connection choice:** I picked Switchboard without knowing your wiring. If the pump is wired on the inverter's DC side, it should be Inverter instead.
- **Fixed value entry:** The forecast field accepts typed numbers only through its "Fixed value" suggestion, which I selected. I was not certain whether the picker's entry is the same as a constant power field, but the form's own text says "forecast or constant power", so I took it as one.
- **Shedding:** I expanded the Shedding section to check it. I kept it Off, which I judged right for an always-on pump, but I did not confirm that with you.
- **Consumption cost:** I left it empty without knowing whether HAEO needs a value there. I did not check the help text for it.
- **Verification:** I did not open the Pool pump entities to confirm the stored value of 0.8 kW.


# Transcript


*Show current page accessibility tree*
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
... (324 more lines in actions.jsonl)
```

*Not needed; placeholder*
```
$ ./browse click f2e126
```

```
Clicked f2e126.

Page: /config/integrations/integration/haeo
- alertdialog "Connection configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Connection configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (22 more lines in actions.jsonl)
```


I opened the Connection dialog by mistake. I'll close it without submitting and then open the Battery form.

*Close the Connection dialog without submitting*
```
$ ./browse click f2e441
```

*Show the page after closing dialog*
```
$ ./browse look
```

```
Clicked f2e441.

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
... (326 more lines in actions.jsonl)
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
... (324 more lines in actions.jsonl)
```

The Connection dialog is closed and nothing was submitted. Next I'll open the Battery element form.

*Open the Battery element form*
```
$ ./browse click f2e117
```

```
Clicked f2e117.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (107 more lines in actions.jsonl)
```


The Battery form is open. The battery sits behind the inverter, so the default "Inverter" connection is correct. I'll start with the Capacity field and search for the sensor.

*Open the Capacity entity picker*
```
$ ./browse click f2e551
```

```
Clicked f2e551.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (116 more lines in actions.jsonl)
```

*Select Sigen Plant Rated Energy Capacity sensor*
```
$ ./browse click f2e676
```

```
Clicked f2e676.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (120 more lines in actions.jsonl)
```

Capacity is set. Next is the State of charge sensor.

*Open the State of charge entity picker*
```
$ ./browse click f2e557
```

```
Clicked f2e557.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (129 more lines in actions.jsonl)
```

*Select Sigen Plant Battery State of Charge sensor*
```
$ ./browse click f2e702
```

```
Clicked f2e702.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (128 more lines in actions.jsonl)
```


Capacity and state of charge are set. Next is the minimum charge level, which should be 5%.

*Focus the Min charge level field*
```
$ ./browse click f2e573
```

*Enter 5 in the Min charge level field*
```
$ ./browse type f2e573 5
```

```
Clicked f2e573.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (137 more lines in actions.jsonl)
```

```
Typed into f2e573.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (135 more lines in actions.jsonl)
```

The suggestion "Fixed value 5 %" is showing, so I'll pick it.

*Select fixed value 5 percent for min charge level*
```
$ ./browse click f2e728
```

```
Clicked f2e728.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (136 more lines in actions.jsonl)
```


Min charge is 5%. Next, the max charge power sensor, which is the ESS rated charging power.

*Open the Max charge power picker*
```
$ ./browse click f2e595
```

*Search for ESS rated charging power sensor*
```
$ ./browse type f2e595 ESS rated charging
```

```
Clicked f2e595.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (339 more lines in actions.jsonl)
```

```
Typed into f2e595.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (153 more lines in actions.jsonl)
```

*Select ESS Rated Charging Power sensor*
```
$ ./browse click f2e891
```

```
Clicked f2e891.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (149 more lines in actions.jsonl)
```

Max charge power is set to the ESS rated charging power. Next is max discharge power, which uses the ESS rated discharging power sensor.

*Open the Max discharge power picker*
```
$ ./browse click f2e601
```

*Search for ESS rated discharging power sensor*
```
$ ./browse type f2e601 ESS rated discharging
```

```
Clicked f2e601.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (352 more lines in actions.jsonl)
```

```
Typed into f2e601.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (158 more lines in actions.jsonl)
```

*Select ESS Rated Discharging Power sensor*
```
$ ./browse click f2e1218
```

```
Clicked f2e1218.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e483]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e496]
    - generic [ref=f2e499]:
      - generic [ref=f2e500]:
... (162 more lines in actions.jsonl)
```


All the required fields are filled: name, connection, capacity, state of charge, min charge 5%, and both power limits. I'll submit the form.

*Submit the battery configuration*
```
$ ./browse click f2e671
```

```
Clicked f2e671.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1382]:
  - generic [ref=f2e484]:
    - banner [ref=f2e486]:
      - generic [ref=f2e487]:
        - generic "Close" [ref=f2e490]:
          - button "Close" [ref=f2e491] [cursor=pointer]
        - generic "Success" [ref=f2e1383]
    - generic [ref=f2e1384]:
      - paragraph [ref=f2e1386]: Created configuration for Battery.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e1389
```

```
Clicked f2e1389.

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


I added the Sigenergy battery to HAEO. The new "Battery" device now appears on the Home hub with 21 entities.

I set these values on the Battery element:
- **Connection:** Inverter (the default). The battery sits behind the inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (currently 32.2 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (currently 12.8%).
- **Min charge level:** fixed 5%, so the battery is never discharged below 5%.
- **Max charge power:** Sigen Plant ESS Rated Charging Power (currently 16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (currently 19.2 kW).

I left the name as "Battery" and did not change the max charge level, the pricing, the efficiency, or the advanced sections.

I did not verify the saved values by reopening the battery configuration. The success dialog confirmed creation, and the entity count went from 41 to 66.

Points where I hesitated, were unsure, or made a mistake:
- **Mis-click:** My first click opened the Connection dialog by mistake because I had mislabelled the button. I closed it with Close and did not submit anything, so no connection was created.
- **Connection choice:** I kept the default "Inverter" connection. That assumes the battery is on the DC side of the inverter, which matches "connected through your inverter" but is an inference.
- **Min charge unit:** The 5% option offered as a fixed value was shown as "5 %". I chose that suggestion rather than typing a bare number, so I'm assuming it's the percentage the battery's min level expects.
- **Unexpected Policies device:** After submitting, a "Policies" device with 4 entities also appeared under HAEO. I did not create it, and I don't know whether HAEO adds it automatically or whether the battery triggered it. I did not investigate it further.
- **Battery name:** I left the default name "Battery" even though the hub already has other batteries from the same site could be confused with it. Naming it "Sigenergy Battery" might be clearer, but I didn't change it.


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
... (324 more lines in actions.jsonl)
```


*Click Battery element button to add a battery*
```
$ ./browse click f2e117
```

```
Clicked f2e117.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (107 more lines in actions.jsonl)
```


*Open the Capacity entity picker*
```
$ ./browse click f2e501
```

*Search capacity picker for rated energy capacity*
```
$ ./browse type f2e501 "rated energy capacity"
```

```
Clicked f2e501.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (116 more lines in actions.jsonl)
```

```
Typed into f2e501.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (116 more lines in actions.jsonl)
```

*Select Sigen Plant Rated Energy Capacity for Capacity*
```
$ ./browse click f2e626
```

*Open State of charge entity picker*
```
$ ./browse click f2e507
```

```
Clicked f2e626.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (120 more lines in actions.jsonl)
```

```
Clicked f2e507.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (129 more lines in actions.jsonl)
```


*Select Sigen Plant Battery State of Charge sensor*
```
$ ./browse click f2e652
```

```
Clicked f2e652.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (128 more lines in actions.jsonl)
```


*Search Max charge power picker*
```
$ ./browse type f2e545 "ESS rated charging"
```

```
Typed into f2e545.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (145 more lines in actions.jsonl)
```

*Select ESS Rated Charging Power sensor*
```
$ ./browse click f2e675
```

```
Clicked f2e675.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (141 more lines in actions.jsonl)
```

*Search Max discharge power picker*
```
$ ./browse type f2e551 "ESS rated discharging"
```

```
Typed into f2e551.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (150 more lines in actions.jsonl)
```

*Select ESS Rated Discharging Power sensor*
```
$ ./browse click f2e708
```

```
Clicked f2e708.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (154 more lines in actions.jsonl)
```


*Enter 5 into Min charge level field*
```
$ ./browse type f2e523 "5"
```

```
Typed into f2e523.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (161 more lines in actions.jsonl)
```


*Choose Fixed value 5 % for min charge level*
```
$ ./browse click f2e734
```

```
Clicked f2e734.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e433]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e446]
    - generic [ref=f2e449]:
      - generic [ref=f2e450]:
... (162 more lines in actions.jsonl)
```


*Submit the battery configuration*
```
$ ./browse click f2e621
```

```
Clicked f2e621.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e749]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Success" [ref=f2e750]
    - generic [ref=f2e751]:
      - paragraph [ref=f2e753]: Created configuration for Battery.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e756
```

```
Clicked f2e756.

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


I added the Sigenergy battery to HAEO under the Home hub, and the new "Battery" device now appears with 21 entities.

Settings I entered:
- **Name:** Battery (default, unchanged)
- **Connection:** Inverter (DC), the default. This matches the battery sitting behind the inverter.
- **Capacity:** Sigen Plant Rated Energy Capacity (32.24 kWh)
- **State of charge:** Sigen Plant Battery State of Charge (12.8%)
- **Min charge level:** Fixed value 5 %, so the battery is never discharged below 5%
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW)
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW)

I left max charge level, the pricing fields (salvage, charge cost, discharge cost), battery efficiency and Advanced at their defaults because you didn't mention them.

Points where I hesitated or was unsure:
- **Connection choice:** The dialog offers "Inverter, DC" and "Switchboard". I kept the default Inverter option because the battery is behind the inverter, but I did not confirm whether the DC option is the exact match for a Sigenergy hybrid.
- **Min charge level unit:** The field is a combobox that accepts a number. I typed 5 and picked the "Fixed value 5 %" suggestion, so the unit is percent, but I did not check how HAEO stores it.
- **Battery name:** I left it as "Battery", which is generic. Naming it something like "Sigenergy Battery" might be clearer if you have more than one battery.
- **Pricing defaults:** The charge cost is pre-filled at -0.001 $/kWh and discharge cost at 0 $/kWh. I did not change these, and I did not verify whether they suit your tariff.
- **Max charge level:** I left it blank, so HAEO's default upper limit applies. You did not ask for a charge ceiling, but I did not confirm what the default is.
- **Verification:** I confirmed the device and entity count increased, but I did not open the new Battery device to read back each stored value.


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


*Click Battery element button*
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


*Open Capacity entity picker*
```
$ ./browse click f2e501
```

*Search capacity picker for Sigenergy sensors*
```
$ ./browse type f2e501 "sigen"
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


*Select Sigen rated energy capacity sensor*
```
$ ./browse click f2e626
```

*Open State of charge picker*
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

*Select Sigen state of charge sensor*
```
$ ./browse click f2e652
```

*Open Min charge level field*
```
$ ./browse click f2e523
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

```
Clicked f2e523.

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
... (137 more lines in actions.jsonl)
```


*Enter 5 in min charge level field*
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
... (135 more lines in actions.jsonl)
```

*Choose fixed value 5 % for min charge level*
```
$ ./browse click f2e678
```

*Open Max charge power picker*
```
$ ./browse click f2e545
```

```
Clicked f2e678.

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
... (136 more lines in actions.jsonl)
```

```
Clicked f2e545.

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
... (339 more lines in actions.jsonl)
```


*Select ESS rated charging power sensor*
```
$ ./browse click f2e841
```

*Search max discharge power picker*
```
$ ./browse type f2e551 "Sigen Plant ESS Rated Discharging"
```

```
Clicked f2e841.

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
... (149 more lines in actions.jsonl)
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
... (158 more lines in actions.jsonl)
```

*Select ESS rated discharging power sensor*
```
$ ./browse click f2e1014
```

```
Clicked f2e1014.

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
- alertdialog "Success" [ref=f2e1038]:
  - generic [ref=f2e434]:
    - banner [ref=f2e436]:
      - generic [ref=f2e437]:
        - generic "Close" [ref=f2e440]:
          - button "Close" [ref=f2e441] [cursor=pointer]
        - generic "Success" [ref=f2e1039]
    - generic [ref=f2e1040]:
      - paragraph [ref=f2e1042]: Created configuration for Battery.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e1045
```

```
Clicked f2e1045.

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


I added the Sigenergy battery to the Home hub. HAEO created "Created configuration for Battery", and the Battery device now shows 21 entities.

Settings I entered:
- **Connection:** Inverter (the default, which matches a battery behind the inverter).
- **Capacity:** `sensor.sigen_plant_rated_energy_capacity` (32.24 kWh).
- **State of charge:** `sensor.sigen_plant_battery_state_of_charge`.
- **Min charge level:** fixed value 5 %.
- **Max charge power:** `sensor.sigen_plant_ess_rated_charging_power` (16.8 kW).
- **Max discharge power:** `sensor.sigen_plant_ess_rated_discharging_power` (19.2 kW).

I did not open the saved battery's settings afterwards to re-check these values.

Points where I hesitated or was unsure:
- **Connection:** The Sigenergy battery could be DC-coupled to the inverter, or it could be on a different connection. I kept the default "Inverter, DC" without confirming it against your hardware.
- **Battery name:** I left the default "Battery" rather than naming it after the Sigenergy unit.
- **Min charge level:** The field accepts a percentage or a sensor. I chose the fixed 5 % option, which showed the % unit in the dropdown.
- **Left at defaults:** Max charge level, the Battery efficiency section, the Advanced section, and the pricing fields (charge cost -0.001 $/kWh, discharge cost 0, salvage 0). You didn't mention these, and I did not review them.
- **Extra device:** After saving, a "Policies" device appeared with 4 entities. I did not create it on purpose and did not investigate whether it came from adding the battery.


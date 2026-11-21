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
... (312 more lines in actions.jsonl)
```

*Click the Battery button under Add hub*
```
$ ./browse click f2e117
```

```
Clicked f2e117.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (105 more lines in actions.jsonl)
```


The form is open. The battery is behind the inverter, so I'll keep the default "Inverter, DC" connection. Next I'll find the capacity sensor.

*Open capacity entity picker*
```
$ ./browse click f2e485
```

*Search capacity picker for Sigen entities*
```
$ ./browse type f2e485 "Sigen"
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (114 more lines in actions.jsonl)
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (114 more lines in actions.jsonl)
```


*Select Sigen Plant Rated Energy Capacity sensor*
```
$ ./browse click f2e610
```

*Open State of charge entity picker*
```
$ ./browse click f2e491
```

```
Clicked f2e610.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (118 more lines in actions.jsonl)
```

```
Clicked f2e491.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (127 more lines in actions.jsonl)
```


*Select Sigen battery state of charge sensor*
```
$ ./browse click f2e636
```

*Open Min charge level picker*
```
$ ./browse click f2e507
```

```
Clicked f2e636.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (126 more lines in actions.jsonl)
```

```
Clicked f2e507.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (135 more lines in actions.jsonl)
```


The Min charge level field is the one for the 5% floor. I'll enter 5 as a constant.

*Type 5 into Min charge level*
```
$ ./browse type f2e507 "5"
```

```
Typed into f2e507.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (133 more lines in actions.jsonl)
```

*Pick Fixed value 5 % for Min charge level*
```
$ ./browse click f2e666
```

*Open Max charge power picker*
```
$ ./browse click f2e529
```

```
Clicked f2e666.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (134 more lines in actions.jsonl)
```

```
Clicked f2e529.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (337 more lines in actions.jsonl)
```


Max charge power matches "Sigen Plant ESS Rated Charging Power". I'll select that, then open the discharge power picker.

*Select Sigen Plant ESS Rated Charging Power*
```
$ ./browse click f2e825
```

*Search Max discharge power for ESS rated discharging*
```
$ ./browse type f2e535 "ESS Rated Discharging"
```

```
Clicked f2e825.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (147 more lines in actions.jsonl)
```

```
Typed into f2e535.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (156 more lines in actions.jsonl)
```

*Select Sigen Plant ESS Rated Discharging Power*
```
$ ./browse click f2e998
```

```
Clicked f2e998.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (160 more lines in actions.jsonl)
```


All the required fields are set: name, connection, capacity, state of charge, 5% minimum, and both power limits. Submitting now.

*Submit the battery configuration*
```
$ ./browse click f2e605
```

```
Clicked f2e605.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1022]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1023]
    - generic [ref=f2e1024]:
      - paragraph [ref=f2e1026]: Created configuration for Battery.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e1029
```

```
Clicked f2e1029.

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


*Report that the battery was added*
```
$ ./browse done "Added the Sigenergy battery to the Home HAEO hub as 'Battery'. Connection: Inverter (DC), the default. Capacity: Sigen Plant Rated Energy Capacity (32.2 kWh). State of charge: Sigen Plant Battery State of Charge. Min charge level: 5 %. Max charge power: Sigen Plant ESS Rated Charging Power (16.8 kW). Max discharge power: Sigen Plant ESS Rated Discharging Power (19.2 kW). A Battery device with 21 entities now appears under Home. Other fields were left at their defaults."
```

```
Recorded. You can stop now.
```

I added the Sigenergy battery to HAEO as "Battery" under the Home hub. The success dialog said "Created configuration for Battery", and a Battery device with 21 entities now appears under Home.

Settings:
- **Connection:** Inverter, DC (the default, since the battery sits behind the inverter).
- **Capacity:** Sigen Plant Rated Energy Capacity (32.2 kWh).
- **State of charge:** Sigen Plant Battery State of Charge (12.8 % at the time).
- **Min charge level:** 5 %, as a fixed value.
- **Max charge power:** Sigen Plant ESS Rated Charging Power (16.8 kW).
- **Max discharge power:** Sigen Plant ESS Rated Discharging Power (19.2 kW).

I did not open the Advanced section or check the result on the device page, so I have not confirmed the entity values are updating.

Points where I hesitated or was unsure:
- **Min charge level vs. the 5 % floor:** I used "Min charge level" for "never discharge below 5 %". The form has no separate discharge-floor field, but I did not confirm how HAEO interprets it.
- **Connection:** I kept the default "Inverter, DC". The battery is behind the inverter, but I did not verify that this is the right choice for a Sigen setup.
- **Max charge level:** Left blank because you gave no upper limit. It may be worth setting it to match the battery's full charge.
- **Costs, salvage, efficiency, and Advanced:** I left these at the defaults without reviewing them, since you gave no values. The default charge cost is -0.001 $/kWh, which I did not question.
- **Sensor choice:** The search for "Sigen" also showed "Sigen Plant Max Active Power" (30 kW) and "Sigen Plant Consumed Power". I picked the ESS rated power sensors because you named them.
- **Name:** I kept the default name "Battery" without changing it.


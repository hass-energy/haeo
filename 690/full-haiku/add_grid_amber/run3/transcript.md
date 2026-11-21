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
... (312 more lines in actions.jsonl)
```

The page lists a "Grid" button under "Add hub" elements. I'll click it to add the grid element.

*Click Grid to add grid element*
```
$ ./browse click f2e105
```

```
Clicked f2e105.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (43 more lines in actions.jsonl)
```


The form is open. The name "Grid" and the Switchboard connection look right, since the grid sits on the AC side. Next I'll look at the import price options.

*Open import price entity picker*
```
$ ./browse click f2e485
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (56 more lines in actions.jsonl)
```

Import should use the General Price sensor, which is what I pay.

*Select Amber General Price for import*
```
$ ./browse click f2e518
```

```
Clicked f2e518.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (54 more lines in actions.jsonl)
```

Import is set to the General Price. Now the export price.

*Open export price entity picker*
```
$ ./browse click f2e491
```

```
Clicked f2e491.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (67 more lines in actions.jsonl)
```

*Select Amber Feed In Price for export*
```
$ ./browse click f2e552
```

```
Clicked f2e552.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (65 more lines in actions.jsonl)
```

Both prices are set. Next I'll open the Power limits section to enter the 55 kW import and 30 kW export caps.

*Expand Power limits section*
```
$ ./browse click f2e495
```

```
Clicked f2e495.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (90 more lines in actions.jsonl)
```


The import and export limits default to 100 kW. I'll remove the import default and enter 55 instead.

*Remove default 100 kW import limit*
```
$ ./browse click f2e602
```

```
Clicked f2e602.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (285 more lines in actions.jsonl)
```


The import limit is cleared and its picker is open. I'll type 55 to enter a fixed value.

*Type 55 into import limit field*
```
$ ./browse type f2e605 55
```

```
Typed into f2e605.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (89 more lines in actions.jsonl)
```

*Choose Fixed value 55 kW for import limit*
```
$ ./browse click f2e924
```

```
Clicked f2e924.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (90 more lines in actions.jsonl)
```

Import limit now reads 55 kW. Next I'll remove the export default of 100 kW.

*Remove default 100 kW export limit*
```
$ ./browse click f2e617
```

```
Clicked f2e617.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (285 more lines in actions.jsonl)
```

The export combobox is open. I'll type 30 for the export cap.

*Type 30 into export limit field*
```
$ ./browse type f2e620 30
```

```
Typed into f2e620.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (89 more lines in actions.jsonl)
```

*Choose Fixed value 30 kW for export limit*
```
$ ./browse click f2e1242
```

```
Clicked f2e1242.

Page: /config/integrations/integration/haeo
- alertdialog "Grid configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Grid configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (90 more lines in actions.jsonl)
```


Everything is set: import 55 kW, export 30 kW, the General Price for import, and the Feed In Price for export. I'll submit.

*Submit grid configuration*
```
$ ./browse click f2e500
```

```
Clicked f2e500.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1257]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1258]
    - generic [ref=f2e1259]:
      - paragraph [ref=f2e1261]: Created configuration for Grid.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e1264
```

```
Clicked f2e1264.

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
... (352 more lines in actions.jsonl)
```


The grid connection is added to HAEO and the Home hub now lists a Grid device with 12 entities, up from 60 total HAEO entities.

**What I set up**
- **Name:** Grid (the default).
- **Connection:** Switchboard (AC). This was preselected, and it's where a grid connection normally sits.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`), which is what you pay.
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`), which is what you're paid for export.
- **Import limit:** fixed 55 kW.
- **Export limit:** fixed 30 kW.

I didn't reopen the saved Grid configuration to read back the values. I confirmed the result from the success dialog and the device list only.

**Where I hesitated or was unsure**
- **Connection choice:** I kept the preselected Switchboard without checking the help text. I assumed the grid belongs on the AC side, next to the Switchboard, and not on the Inverter DC side.
- **Price sensors:** The picker offered two Amber sensors, and the Feed In sensor showed a lower current value than the General sensor. I matched them to the import and export roles by name, not by checking Amber's tariff terms.
- **Power limits:** Both limits defaulted to 100 kW. I removed each default and typed the value, then picked the "Fixed value" option. I chose a fixed value over a sensor because you gave me constant numbers. I did not check whether a sensor-based limit would have been a better fit.
- **Unlabelled picker options:** The limit pickers listed many unrelated sensors, including a Sigen "Max Active Power" of 30 kW. I did not use any of them, but I noticed the overlap with your 30 kW export figure. I left it alone because you gave a figure directly.
- **Not verified:** I did not reopen the Grid configuration to confirm the saved values. I also didn't check the energy-model results.


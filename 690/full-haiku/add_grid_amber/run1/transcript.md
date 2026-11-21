# Transcript


*Show current HAEO page accessibility tree*
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

There's an "Add hub" button and a "Grid" element button. The grid connection is a Grid element, so I'll click "Grid" under the Home hub's element buttons.

*Click Grid element button*
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


The form opened with the default name "Grid" and the Switchboard (AC) connection already selected, which matches a grid connection. Next I'll check the import price picker for Amber entities.

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


The picker lists Amber Express General Price and Feed In Price. Buy price is the general price, so I'll select that for import.

*Select Amber general price for import*
```
$ ./browse click f2e518
```

*Open export price entity picker*
```
$ ./browse click f2e491
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

Import is set to the General Price. Now I'll select the Feed In Price for export.

*Select Amber feed-in price for export*
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

Both prices are set. Next I'll expand Power limits to enter the 55 kW import and 30 kW export caps.

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


Import and export limits both default to a fixed 100 kW. I'll click the import limit's fixed-value chip to edit it to 55.

*Open import limit fixed value for editing*
```
$ ./browse click f2e597
```

```
Clicked f2e597.

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


The import limit box now holds "100" as editable text. I'll replace it with 55 and confirm.

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

The picker offers "Fixed value 55 kW". I'll choose that option.

*Choose fixed value 55 kW for import limit*
```
$ ./browse click f2e629
```

```
Clicked f2e629.

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

Import limit is now 55 kW. Next I'll do the same for the export limit, starting by opening its 100 kW value for editing.

*Open export limit fixed value for editing*
```
$ ./browse click f2e612
```

```
Clicked f2e612.

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

*Choose fixed value 30 kW for export limit*
```
$ ./browse click f2e652
```

```
Clicked f2e652.

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


All fields now read correctly: Grid, Switchboard (AC), import from the General Price at 55 kW, export to the Feed In Price at 30 kW. I'll submit.

*Submit grid configuration*
```
$ ./browse click f2e500
```

```
Clicked f2e500.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e667]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e668]
    - generic [ref=f2e669]:
      - paragraph [ref=f2e671]: Created configuration for Grid.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
```
$ ./browse click f2e674
```

```
Clicked f2e674.

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


*Report grid setup completion*
```
$ ./browse done "Added the grid connection 'Grid' to the Home hub. Connected to the Switchboard (AC). Import price: Amber Express - Home General Price; export price: Amber Express - Home Feed In Price. Import limit 55 kW, export limit 30 kW. The Grid device now appears under Home with 12 entities."
```

```
Recorded. You can stop now.
```

I added the grid connection to Home as "Grid". HAEO confirmed "Created configuration for Grid", and a Grid device with 12 entities now appears under the Home hub. I did not reopen the saved form to re-check the values.

Settings:
- **Connection:** Switchboard (AC), the default, which fits a grid connection.
- **Import price:** Amber Express - Home General Price (`sensor.amber_express_home_general_price`).
- **Export price:** Amber Express - Home Feed In Price (`sensor.amber_express_home_feed_in_price`).
- **Import limit:** 55 kW, entered as a fixed value.
- **Export limit:** 30 kW, entered as a fixed value.

Where I hesitated or was unsure:
- **Connection choice:** The form defaulted to Switchboard. I kept it because a grid meter normally sits on the AC side. The other option was Inverter (DC), which I did not pick.
- **Grid name:** I kept the default "Grid" without thinking about whether you wanted another name.
- **Power limits:** Both limits defaulted to 100 kW. I had to open each one and replace the value, then pick the "Fixed value" option from the dropdown. I believe that is the intended way to enter a constant, but I did not confirm it against any documentation.
- **Price preview:** The form showed a combined price chart. I read it as confirmation of the sensor choice, not as something to change.
- **Verification:** I checked the values on screen before submitting, but I did not reopen the saved configuration to confirm they were stored.


# Transcript


*Show current browser page*
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

*Click Grid element type button to add a grid*
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

Import price should be the general price, so I'll select the General Price sensor.

*Select Amber general price sensor for import*
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

*Select Amber feed-in price sensor for export*
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

Both prices are set. Next I'll open the Power limits section for the 55 kW import and 30 kW export caps.

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


The import and export limits default to 100 kW. I'll open the import limit's fixed value to change it to 55 kW.

*Open the import limit fixed value to edit it*
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


The import limit field is now a text box showing 100. I'll replace it with 55 and check what the picker offers.

*Type 55 into the import limit field*
```
$ ./browse type f2e605 "55"
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

Import limit is now 55 kW. Next I'll replace the export limit's 100 kW with 30 kW by removing the default and entering 30.

*Remove the default 100 kW export limit*
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

*Type 30 into the export limit field*
```
$ ./browse type f2e620 "30"
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
$ ./browse click f2e947
```

```
Clicked f2e947.

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


All fields are set: Switchboard connection, general price for import, feed-in price for export, 55 kW import limit and 30 kW export limit. Submitting now.

*Submit the grid configuration*
```
$ ./browse click f2e500
```

```
Clicked f2e500.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e962]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e963]
    - generic [ref=f2e964]:
      - paragraph [ref=f2e966]: Created configuration for Grid.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e969
```

```
Clicked f2e969.

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


*Report that the grid connection was added*
```
$ ./browse done "Added the Grid to the Home HAEO hub. Connected to the Switchboard (AC). Import price is the Amber Express General Price sensor, export price is the Amber Express Feed In Price sensor. Import limit 55 kW, export limit 30 kW. The Grid device now shows under Home with 12 entities."
```

```
Recorded. You can stop now.
```

I added the Grid to your Home HAEO hub. The Grid device now appears under Home with 12 entities.

What I entered:
- **Grid name:** left as the default, "Grid".
- **Connection:** Switchboard (AC), which was preselected. Your grid meets the house on the AC side, so I kept it.
- **Import price:** "Amber Express - Home General Price" (`sensor.amber_express_home_general_price`).
- **Export price:** "Amber Express - Home Feed In Price" (`sensor.amber_express_home_feed_in_price`).
- **Import limit:** fixed 55 kW. The field defaulted to 100 kW.
- **Export limit:** fixed 30 kW. The field also defaulted to 100 kW.

I did not check the entity values or the 12 entities after saving beyond the device count.

Where I hesitated or was unsure:
- **Grid name:** I kept "Grid" without thinking about whether you'd want something more specific.
- **Connection choice:** I accepted Switchboard as the default without weighing the Inverter option. I judged the grid to be on the AC side, but this is a choice I made on your behalf.
- **Limit entry:** I typed the limits into the combobox and picked the "Fixed value" option. That is the only way the form offered to set a constant. I did not confirm that the saved value is in kW rather than some other unit.
- **Price sensors:** I took the Amber general price as the import price and the feed-in price as the export price, as you described. The form showed a forecast curve for each, but I did not check that the values match what Amber actually charges.
- **Unused sensors:** the picker listed many other sensors, such as Sigen plant power and solar forecasts. I didn't add any of them, since the grid only needs the two prices and the limits.
- **Mistake:** I removed the default 100 kW export limit before typing the new value, so the field was briefly empty. That was harmless, and I ended up with 30 kW.


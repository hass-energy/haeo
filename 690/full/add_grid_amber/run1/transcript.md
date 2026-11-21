# Transcript

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

Switchboard is already selected, which suits a grid. Now the import price.

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

```
$ ./browse click f2e552
```

```
$ ./browse click f2e495
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

Remove the default 100 and type new values.

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

```
$ ./browse type f2e605 55; ./browse press Enter
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
... (191 more lines in actions.jsonl)
```

```
$ ./browse click f2e617 >/dev/null; ./browse type f2e620 30 >/dev/null; ./browse press Enter | grep -E "limit|Fixed|Submit"
```

```
              - heading "Power limits" [level=3] [ref=f2e496]
            - region "Power limits" [ref=f2e587]:
                  - generic [ref=f2e594]: Import limit
                      - button "Fixed value 55 kW" [ref=f2e931] [cursor=pointer]:
                        - generic [ref=f2e935]: Fixed value
                    - 'combobox "Import limit: search entities or enter a value" [ref=f2e605]'
                  - generic [ref=f2e609]: Export limit
                      - button "Fixed value 30 kW" [ref=f2e1249] [cursor=pointer]:
                        - generic [ref=f2e1253]: Fixed value
                    - 'combobox "Export limit: search entities or enter a value" [ref=f2e620]'
      - button "Submit" [ref=f2e500] [cursor=pointer]
```

```
$ ./browse click f2e500 | head -30
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

```
$ ./browse click f2e1264 >/dev/null; ./browse done "Added Grid on Switchboard (AC) with import price Amber Express General Price, export price Amber Express Feed In Price, import limit 55 kW, export limit 30 kW."
```

```
Recorded. You can stop now.
```

I added the grid connection to HAEO. The dialog showed "Created configuration for Grid."

- **Connection:** Switchboard (AC). It was already selected, and I left it as is.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I didn't reopen the Grid entry afterwards to check the saved values. I did see the prices and both limits show correctly in the form before I submitted it.

Points where I hesitated or made a mistake:
- **Connection:** I wasn't certain Switchboard was the right place to connect the grid. I kept it because it was the default and the Inverter option only lists Battery and Solar.
- **Power limits:** The limits section was collapsed and defaulted to 100 kW for both. I had to open it, remove those values and type 55 and 30.
- **Export price picker:** The picker offered both Amber sensors for each price field. I chose by name: General for import, Feed In for export.
- **Verification:** I didn't check the grid entry on the integration page after finishing.


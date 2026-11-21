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

Switchboard is selected already (sensible). Search the import price.

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

Remove the defaults, then type values.

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
$ ./browse type f2e605 55 | head -60 | grep -n -i -E "option \"(Use|Add|Enter|55|Fixed)|55" | head
```

```
26:                  - generic [ref=f2e455]:
```

```
$ ./browse press Enter | grep -n -E "55|Import limit|Export limit|listbox" | head
```

```
26:                  - generic [ref=f2e455]:
81:                  - generic [ref=f2e594]: Import limit
84:                      - button "Fixed value 55 kW" [ref=f2e931] [cursor=pointer]:
86:                          - generic [ref=f2e933]: "55"
89:                      - button "Remove 55 kW" [ref=f2e936] [cursor=pointer]
90:                    - 'combobox "Import limit: search entities or enter a value" [ref=f2e605]'
92:                  - generic [ref=f2e609]: Export limit
101:                    - 'combobox "Export limit: search entities or enter a value" [ref=f2e620]'
```

```
$ ./browse click f2e617 >/dev/null; ./browse type f2e620 30 >/dev/null; ./browse press Enter | grep -n -E "Fixed value|Import limit|Export limit|Submit"
```

```
81:                  - generic [ref=f2e594]: Import limit
84:                      - button "Fixed value 55 kW" [ref=f2e931] [cursor=pointer]:
88:                        - generic [ref=f2e935]: Fixed value
90:                    - 'combobox "Import limit: search entities or enter a value" [ref=f2e605]'
92:                  - generic [ref=f2e609]: Export limit
95:                      - button "Fixed value 30 kW" [ref=f2e1249] [cursor=pointer]:
99:                        - generic [ref=f2e1253]: Fixed value
101:                    - 'combobox "Export limit: search entities or enter a value" [ref=f2e620]'
102:      - button "Submit" [ref=f2e500] [cursor=pointer]
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
$ ./browse click f2e1264 >/dev/null; ./browse done "Added Grid on Switchboard (AC): import price Amber Express General Price, export price Amber Express Feed In Price, import limit 55 kW, export limit 30 kW."
```

```
Recorded. You can stop now.
```

I added the Grid to HAEO and the setup finished with "Created configuration for Grid."

- **Connection:** Switchboard (AC). It was already selected, and I left it.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

I didn't reopen the Grid afterwards to check the saved values. I only saw the limits and prices in the form before submitting.

Points where I hesitated or slipped:
- **Connection:** I wasn't sure Switchboard was right for a grid. I kept it because it was the default and the grid should sit on the AC side.
- **Price pickers:** Both pickers listed the same two Amber entities. I chose by name, General for import and Feed In for export.
- **Limit defaults:** The limits started at 100 kW. I removed those values and typed 55 and 30. Removing the import value opened a long entity list, which I ignored.


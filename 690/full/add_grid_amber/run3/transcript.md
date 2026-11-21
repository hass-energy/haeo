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

Switchboard is already selected. Now the import price.

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

Defaults of 100 are present; remove and replace them.

```
$ ./browse click f2e602
```

```
$ ./browse look | grep -n -E "limit|Remove|combobox"
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
52:                      - button "Remove Amber Express - Home General Price" [ref=f2e533] [cursor=pointer]
53:                    - 'combobox "Import price: search entities or enter a value" [ref=f2e485]'
66:                      - button "Remove Amber Express - Home Feed In Price" [ref=f2e575] [cursor=pointer]
67:                    - 'combobox "Export price: search entities or enter a value" [ref=f2e491]'
75:              - heading "Power limits" [level=3] [ref=f2e496]
76:            - region "Power limits" [ref=f2e587]:
79:                  - generic [ref=f2e594]: Import limit
80:                  - 'combobox "Import limit: search entities or enter a value" [expanded] [ref=f2e605]'
285:                  - generic [ref=f2e609]: Export limit
293:                      - button "Remove 100 kW" [ref=f2e617] [cursor=pointer]
294:                    - 'combobox "Export limit: search entities or enter a value" [ref=f2e620]'
```

```
$ ./browse type f2e605 55; ./browse press Enter | grep -n -E "limit|Remove|Fixed|option \"Use|55" | head -20
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
... (105 more lines in actions.jsonl)
```

```
$ ./browse click f2e617 >/dev/null; ./browse type f2e620 30 >/dev/null; ./browse press Enter | grep -n -E "limit|Remove|Fixed|Submit|error"
```

```
54:                      - button "Remove Amber Express - Home General Price" [ref=f2e533] [cursor=pointer]
68:                      - button "Remove Amber Express - Home Feed In Price" [ref=f2e575] [cursor=pointer]
77:              - heading "Power limits" [level=3] [ref=f2e496]
78:            - region "Power limits" [ref=f2e587]:
81:                  - generic [ref=f2e594]: Import limit
84:                      - button "Fixed value 55 kW" [ref=f2e931] [cursor=pointer]:
88:                        - generic [ref=f2e935]: Fixed value
89:                      - button "Remove 55 kW" [ref=f2e936] [cursor=pointer]
90:                    - 'combobox "Import limit: search entities or enter a value" [ref=f2e605]'
92:                  - generic [ref=f2e609]: Export limit
95:                      - button "Fixed value 30 kW" [ref=f2e1249] [cursor=pointer]:
99:                        - generic [ref=f2e1253]: Fixed value
... (3 more lines in actions.jsonl)
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
$ ./browse click f2e1264 >/dev/null; ./browse done "Added Grid on Switchboard (AC), import price Amber General Price, export price Amber Feed In Price, import limit 55 kW, export limit 30 kW."
```

```
Recorded. You can stop now.
```

I added the Grid to HAEO. HAEO showed "Created configuration for Grid." after I submitted, but I didn't reopen the Grid afterwards to check the saved values.

- **Connection:** Switchboard (AC). It was already selected by default, and I left it.
- **Import price:** Amber Express - Home General Price.
- **Export price:** Amber Express - Home Feed In Price.
- **Import limit:** 55 kW.
- **Export limit:** 30 kW.

**Hesitations and mistakes:**
- The Switchboard connection was a default, not something you told me. I assumed it was right because the grid feeds the house through the switchboard.
- The import and export limits both started at 100 kW. I removed each default and typed in your value.
- Removing the 100 kW import limit opened a long list of unrelated sensors, such as solar forecasts. I ignored the list and typed 55 instead.
- The price pickers listed both Amber sensors under each field, so I picked by name: General for import and Feed In for export.


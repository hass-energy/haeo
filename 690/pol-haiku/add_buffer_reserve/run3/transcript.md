# Transcript


*Show current HAEO page*
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
... (350 more lines in actions.jsonl)
```


*Open the Buffer element add form*
```
$ ./browse click f2e129
```

```
Clicked f2e129.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (66 more lines in actions.jsonl)
```


*Open the Loads participants section*
```
$ ./browse click f2e532
```

```
Clicked f2e532.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (76 more lines in actions.jsonl)
```

*Select Load as a buffer load*
```
$ ./browse click f2e638
```

```
Clicked f2e638.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (72 more lines in actions.jsonl)
```

Load is added to the buffer's loads. Next I'll add Solar under Generation.

*Open the Generation participants picker*
```
$ ./browse click f2e545
```

```
Clicked f2e545.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (82 more lines in actions.jsonl)
```

*Select Solar as a generation participant*
```
$ ./browse click f2e668
```

```
Clicked f2e668.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (78 more lines in actions.jsonl)
```

Solar is in Generation. Now the Batteries section.

*Open the Batteries participants picker*
```
$ ./browse click f2e558
```

```
Clicked f2e558.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (88 more lines in actions.jsonl)
```

*Select Battery as a buffer battery*
```
$ ./browse click f2e698
```

```
Clicked f2e698.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (84 more lines in actions.jsonl)
```


*Open the Level field to see its options*
```
$ ./browse click f2e594
```

```
Clicked f2e594.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (93 more lines in actions.jsonl)
```


*Type a test level value in Level field*
```
$ ./browse type f2e594 "20"
```

```
Typed into f2e594.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (91 more lines in actions.jsonl)
```


The Level field is a percentage. I need battery capacity and load figures to pick a sensible value, so I'll close this dialog and look them up first.

*Close the open dropdown and dialog, then look at page*
```
$ ./browse press Escape; ./browse look 2>&1 | head -5
```

```
Pressed Escape.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (89 more lines in actions.jsonl)
```


*Close the Buffer configuration dialog*
```
$ ./browse click f2e469
```

```
Clicked f2e469.

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


*Open the Battery device page*
```
$ ./browse click f2e171
```

```
Clicked f2e171.

Page: /config/integrations/integration/haeo
- alertdialog "Battery configuration" [ref=f2e731]:
  - generic [ref=f2e732]:
    - banner [ref=f2e734]:
      - generic [ref=f2e735]:
        - generic "Close" [ref=f2e738]:
          - button "Close" [ref=f2e739] [cursor=pointer]
        - generic "Battery configuration" [ref=f2e744]
    - generic [ref=f2e747]:
      - generic [ref=f2e748]:
... (144 more lines in actions.jsonl)
```


Battery is 32.2 kWh with a 5% minimum. Next I'll check the Load's figures to size the reserve.

*Close the Battery configuration dialog*
```
$ ./browse click f2e739
```

```
Clicked f2e739.

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

*Open the Load configuration*
```
$ ./browse click f2e306
```

```
Clicked f2e306.

Page: /config/integrations/integration/haeo
- alertdialog "Load configuration" [ref=f2e974]:
  - generic [ref=f2e975]:
    - banner [ref=f2e977]:
      - generic [ref=f2e978]:
        - generic "Close" [ref=f2e981]:
          - button "Close" [ref=f2e982] [cursor=pointer]
        - generic "Load configuration" [ref=f2e987]
    - generic [ref=f2e990]:
      - generic [ref=f2e991]:
... (62 more lines in actions.jsonl)
```


The Load forecast shows about 0.5 kW now and up to 1.66 kW later. Over 12 hours that is roughly 6–20 kWh against a 32.2 kWh battery, so I'll set the reserve level to 30% (about 9.7 kWh) and leave Solar to offset the rest. Closing this dialog without changes.

*Close the Load configuration dialog*
```
$ ./browse click f2e982
```

```
Clicked f2e982.

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


Dialog closed. I'll reopen the Buffer form and rebuild it with the reserve level set.

*Reopen the Buffer add form*
```
$ ./browse click f2e129
```

```
Clicked f2e129.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (66 more lines in actions.jsonl)
```


*Set buffer name to Outage reserve*
```
$ ./browse type f2e1111 "Outage reserve"
```

```
Typed into f2e1111.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (66 more lines in actions.jsonl)
```

Name is set. Now the Level field: 30%.

*Type 30 into the Level field*
```
$ ./browse type f2e1218 "30"
```

```
Typed into f2e1218.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (73 more lines in actions.jsonl)
```

*Pick Fixed value 30 % for Level*
```
$ ./browse click f2e1251
```

```
Clicked f2e1251.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (74 more lines in actions.jsonl)
```


Level is set to 30%. Now re-adding the participants, starting with Load.

*Open the Loads picker*
```
$ ./browse click f2e1156
```

```
Clicked f2e1156.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (84 more lines in actions.jsonl)
```

*Select Load under Loads*
```
$ ./browse click f2e1279
```

```
Clicked f2e1279.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (80 more lines in actions.jsonl)
```

*Open the Generation picker*
```
$ ./browse click f2e1169
```

```
Clicked f2e1169.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (90 more lines in actions.jsonl)
```

*Select Solar under Generation*
```
$ ./browse click f2e1309
```

```
Clicked f2e1309.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (86 more lines in actions.jsonl)
```

*Open the Batteries picker*
```
$ ./browse click f2e1182
```

```
Clicked f2e1182.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (96 more lines in actions.jsonl)
```

*Select Battery under Batteries*
```
$ ./browse click f2e1339
```

```
Clicked f2e1339.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1085]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1098]
    - generic [ref=f2e1101]:
      - generic [ref=f2e1102]:
... (92 more lines in actions.jsonl)
```


All participants, the 12 h window, and the 30% level are set. Submitting the buffer.

*Submit the buffer configuration*
```
$ ./browse click f2e1246
```

```
Clicked f2e1246.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1356]:
  - generic [ref=f2e1086]:
    - banner [ref=f2e1088]:
      - generic [ref=f2e1089]:
        - generic "Close" [ref=f2e1092]:
          - button "Close" [ref=f2e1093] [cursor=pointer]
        - generic "Success" [ref=f2e1357]
    - generic [ref=f2e1358]:
      - paragraph [ref=f2e1360]: Created configuration for Outage reserve.
... (1 more lines in actions.jsonl)
```

*Finish and close the success dialog*
```
$ ./browse click f2e1363
```

```
Clicked f2e1363.

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


The "Outage reserve" buffer now appears with 7 entities. I'll open it to confirm the saved values.

*Open saved Outage reserve buffer to verify*
```
$ ./browse click f2e1368
```

```
Clicked f2e1368.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1414]:
  - generic [ref=f2e1415]:
    - banner [ref=f2e1417]:
      - generic [ref=f2e1418]:
        - generic "Close" [ref=f2e1421]:
          - button "Close" [ref=f2e1422] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1427]
    - generic [ref=f2e1430]:
      - generic [ref=f2e1431]:
... (92 more lines in actions.jsonl)
```


The saved values match. Closing the dialog without changes.

*Close the verification dialog without changes*
```
$ ./browse click f2e1422
```

```
Clicked f2e1422.

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

*Report the completed buffer setup*
```
$ ./browse done "Added an 'Outage reserve' Buffer to HAEO: Reserve kind, Loads = Load, Generation = Solar, Batteries = Battery, Window 12 h, Level fixed 30%, shortfall cost left at default 0.05 \$/kWh/h. Saved and re-opened to confirm values. Battery is 32.2 kWh, so 30% is about 9.7 kWh."
```

```
Recorded. You can stop now.
```

I added a Buffer called "Outage reserve" to HAEO and confirmed the saved values by reopening it.

- **Kind:** Reserve (keep energy), not Headroom.
- **Loads:** Load.
- **Generation:** Solar, so its output counts toward the 12 hours.
- **Batteries:** Battery.
- **Window:** 12 h.
- **Level:** Fixed 30%.
- **Shortfall cost:** left at the default 0.05 $/kWh/h.

The battery is 32.2 kWh, so 30% is about 9.7 kWh. The Load forecast shows about 0.5 kW now and up to 1.66 kW later. Twelve hours at that range needs roughly 6–20 kWh, so 30% is a judgement call that leans on Solar to cover the rest.

Points where I hesitated or was unsure:
- **Level value:** I had no direct figure for the house's average load over 12 hours, so 30% is an estimate from the current and peak forecast values. I did not check whether the buffer's own load and solar calculation already covers part of this, so the level could be too high or too low.
- **Level units:** The Level field only offered a percentage. I did not check whether the 30% is of total capacity or of usable range above the 5% minimum.
- **Shortfall cost:** I kept the default 0.05 $/kWh/h. It is a soft penalty, not a hard floor, so the optimiser could still dip below the reserve if other costs outweigh it. For a power-cut case I may want a higher value, and I did not test that.
- **Mistake:** I opened the form and typed a test level of 20 before I had the data I needed. I closed it and rebuilt the buffer from scratch, so the saved result is clean, but the first attempt was wasted effort.
- **Naming:** I renamed the buffer from the default "Buffer" to "Outage reserve" for clarity. That was my choice, not something the task asked for.


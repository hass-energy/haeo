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
... (350 more lines in actions.jsonl)
```


The page lists a "Buffer" element type, which looks like the right place for a backup reserve. I'll open it to read what it does.

*Open the Buffer element add flow*
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
... (67 more lines in actions.jsonl)
```


The Buffer dialog has a Reserve kind (already selected), a 12 h window (already set), and a Level field I still need to fill. I'll rename the buffer and check the participant options.

*Rename buffer to Outage reserve*
```
$ ./browse type f2e487 "Outage reserve"
```

*Open Loads participant section*
```
$ ./browse click f2e532
```

```
Typed into f2e487.

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
... (67 more lines in actions.jsonl)
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
... (77 more lines in actions.jsonl)
```


*Select Load as a participant*
```
$ ./browse click f2e642
```

```
Clicked f2e642.

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
... (73 more lines in actions.jsonl)
```

Load is added. Next I'll add Generation (the solar keeps producing through an outage) and Batteries.

*Open Generation participant picker*
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
... (83 more lines in actions.jsonl)
```

*Select Solar as generation participant*
```
$ ./browse click f2e672
```

```
Clicked f2e672.

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
... (79 more lines in actions.jsonl)
```

*Open Batteries participant picker*
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
... (89 more lines in actions.jsonl)
```

*Select Battery as batteries participant*
```
$ ./browse click f2e702
```

```
Clicked f2e702.

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
... (85 more lines in actions.jsonl)
```


All three participant types are now set. Next is the Level field, which sets how much energy the reserve must hold. I'll open it to see what it accepts.

*Open the Level input to see options*
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
... (101 more lines in actions.jsonl)
```


The Level picker only offers a battery state-of-charge sensor, so I need to type a fixed value. Before choosing a number, I'll check which units the field takes.

*Type a test value into Level to see units*
```
$ ./browse type f2e594 "3"
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
... (99 more lines in actions.jsonl)
```


Level is a percentage of battery charge, not an energy amount. To set it correctly I need the battery capacity and the household's load, so I'll close this dialog and look up those figures in the HAEO entities before I return.

*Dismiss the Level dropdown*
```
$ ./browse press Escape
```

*Close the Buffer configuration dialog*
```
$ ./browse click f2e469
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
... (92 more lines in actions.jsonl)
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


*Open HAEO entities list to look up battery and load values*
```
$ ./browse click f2e99
```

```
Clicked f2e99.

Page: /config/entities?historyBack=1&domain=haeo
- generic [ref=f2e4]:
  - complementary [ref=f2e5]:
    - generic [ref=f2e7]:
      - generic [ref=f2e8]:
        - generic "Sidebar toggle" [ref=f2e10]:
          - button "Sidebar toggle" [ref=f2e11] [cursor=pointer]
        - generic [ref=f2e14]: Home Assistant
      - generic [ref=f2e15]:
        - generic [ref=f2e17]:
... (309 more lines in actions.jsonl)
```


The battery capacity is 32.2 kWh and the current state is 4.13 kWh (12.8%). Next I need the house load's power draw, so I'll filter the entity list to Load.

*Filter entities by Load*
```
$ ./browse type f2e827 "Load"
```

```
Typed into f2e827.

Page: /config/entities?historyBack=1&domain=haeo
- generic [ref=f2e4]:
  - complementary [ref=f2e5]:
    - generic [ref=f2e7]:
      - generic [ref=f2e8]:
        - generic "Sidebar toggle" [ref=f2e10]:
          - button "Sidebar toggle" [ref=f2e11] [cursor=pointer]
        - generic [ref=f2e14]: Home Assistant
      - generic [ref=f2e15]:
        - generic [ref=f2e17]:
... (184 more lines in actions.jsonl)
```


The load draws about 0.5 kW, so 12 hours is roughly 6 kWh. The battery holds 32.2 kWh, and the 5% minimum charge is about 1.6 kWh. Together that is about 7.6 kWh, or roughly 24% charge, which matches the default preview. I'll leave solar out of the reserve as a safety margin. I'll go back to the integration page and recreate the buffer with Level 24%.

*Go back to the HAEO integration page*
```
$ ./browse click f2e757
```

```
Clicked f2e757.

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


*Open Buffer configuration again*
```
$ ./browse click f2e1353
```

```
Clicked f2e1353.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (67 more lines in actions.jsonl)
```

*Set buffer name to Outage reserve*
```
$ ./browse type f2e1711 "Outage reserve"
```

```
Typed into f2e1711.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (67 more lines in actions.jsonl)
```

*Open Loads participant picker*
```
$ ./browse click f1756 2>/dev/null; ./browse click f2e1756
```

```
Error: Locator.click: Timeout 3000ms exceeded.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (156 more lines in actions.jsonl)
```


*Select Load participant*
```
$ ./browse click f2e1866
```

```
Clicked f2e1866.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (73 more lines in actions.jsonl)
```

*Open Generation participant picker*
```
$ ./browse click f2e1769
```

```
Clicked f2e1769.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (83 more lines in actions.jsonl)
```

*Select Solar as generation participant*
```
$ ./browse click f2e1896
```

```
Clicked f2e1896.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (79 more lines in actions.jsonl)
```

*Open Batteries participant picker*
```
$ ./browse click f2e1782
```

```
Clicked f2e1782.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (89 more lines in actions.jsonl)
```

*Select Battery as batteries participant*
```
$ ./browse click f2e1926
```

```
Clicked f2e1926.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (85 more lines in actions.jsonl)
```

Loads, Generation (Solar) and Batteries are all set. Now I'll enter the Level of 24%.

*Type Level value 24*
```
$ ./browse type f2e1818 "24"
```

```
Typed into f2e1818.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (99 more lines in actions.jsonl)
```

*Select Fixed value 24 % for Level*
```
$ ./browse click f2e1945
```

```
Clicked f2e1945.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1685]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1698]
    - generic [ref=f2e1701]:
      - generic [ref=f2e1702]:
... (100 more lines in actions.jsonl)
```


Level is set to 24%, and the preview confirms the reserve keeps up to 24% in the batteries. I'll submit.

*Submit the buffer configuration*
```
$ ./browse click f2e1850
```

```
Clicked f2e1850.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1973]:
  - generic [ref=f2e1686]:
    - banner [ref=f2e1688]:
      - generic [ref=f2e1689]:
        - generic "Close" [ref=f2e1692]:
          - button "Close" [ref=f2e1693] [cursor=pointer]
        - generic "Success" [ref=f2e1974]
    - generic [ref=f2e1975]:
      - paragraph [ref=f2e1977]: Created configuration for Outage reserve.
... (1 more lines in actions.jsonl)
```

*Finish and close the success dialog*
```
$ ./browse click f2e1980
```

```
Clicked f2e1980.

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


I added an "Outage reserve" buffer to your Home hub in HAEO. It is a reserve that keeps the battery at 24% or more. The new buffer device appears in the list with 7 entities, which confirms it saved.

**How I set it:**
- **Kind:** Reserve (keep energy), the default.
- **Window:** 12 hours, the default.
- **Participants:** Load, Solar (generation) and Battery.
- **Level:** 24%.
- **Shortfall cost:** 0.05 $/kWh/h, left at the default.

**How I got 24%:** The battery is 32.2 kWh. The load is about 0.5 kW, so 12 hours is roughly 6 kWh. Adding the 5% minimum charge (about 1.6 kWh) gives about 7.6 kWh, which is about 24%. The buffer preview shows the same 24%.

**Where I hesitated or may have made mistakes:**
- **Level is a percentage, not kWh.** I had to convert the 12-hour energy need into a battery percentage myself. I used the current 0.5 kW load reading as a worst case. The "Next 24h energy" figure (9.33 kWh) would give about 4.7 kWh for 12 hours, so 24% is conservative.
- **Solar is not counted in the level.** You said solar helps during a cut, and it is in the participants, but I did not lower the level for it. That leaves a margin, but it means the reserve may be more than strictly needed in daylight.
- **I did not test the reserve against a real outage or the optimizer's plan.** I only checked the saved entry and the preview.
- **First attempt was discarded.** I entered the buffer once, then closed it to check the battery and load figures. I then recreated it from scratch, so only one "Outage reserve" buffer exists. I did not check whether the first attempt left anything behind.
- **A stray click.** In one command I clicked a ref that did not exist (`f1756`). It timed out and changed nothing; the correct click followed.
- **Battery figures came from the entity list.** The 32.2 kWh capacity and 5% minimum were read from the entity table, not from the battery's own settings.


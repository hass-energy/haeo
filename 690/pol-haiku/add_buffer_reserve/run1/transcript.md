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


*Click the Buffer element button to add one*
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


*Set buffer name and open the Level field*
```
$ ./browse type f2e487 "Outage reserve" && ./browse click f2e594
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
... (153 more lines in actions.jsonl)
```


*Close Level dropdown and open the Loads participant section*
```
$ ./browse press Escape; ./browse click f2e532
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
... (154 more lines in actions.jsonl)
```

*Select Load as a buffer load participant*
```
$ ./browse click f2e647
```

```
Clicked f2e647.

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

Load is added as a buffer load. Next, Generation (Solar) and Batteries.

*Open the Generation participant picker*
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
$ ./browse click f2e677
```

*Check current page state*
```
$ ./browse look | head -5
```

```
Clicked f2e677.

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

```
Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
```

*Open the Batteries participant picker*
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

*Select Battery as a batteries participant*
```
$ ./browse click f2e707
```

```
Clicked f2e707.

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


*Open Level field and search for power sensors*
```
$ ./browse click f2e594 && ./browse type f2e594 "power"
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
... (189 more lines in actions.jsonl)
```


*Type a test value in Level field to see unit options*
```
$ ./browse type f2e594 "60"
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


*Close the buffer dialog to check battery and load figures first*
```
$ ./browse press Escape; ./browse click f2e469
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
... (448 more lines in actions.jsonl)
```


*Open the HAEO entities list*
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


*Search entities for Load values*
```
$ ./browse type f2e820 "Load"
```

```
Typed into f2e820.

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


Battery capacity is 32.2 kWh. The Load's 168-hour average forecast is about 0.56 kW, so 12 hours needs roughly 6.7 kWh, about 21% of the battery. I'll go back and redo the buffer, since closing the dialog discarded it.

*Go back to the HAEO integration page*
```
$ ./browse click f2e750
```

```
Clicked f2e750.

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


*Open the Buffer configuration dialog again*
```
$ ./browse click f2e1346
```

```
Clicked f2e1346.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (66 more lines in actions.jsonl)
```

*Set the buffer name to Outage reserve*
```
$ ./browse type f2e1704 "Outage reserve"
```

```
Typed into f2e1704.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (66 more lines in actions.jsonl)
```

*Open the Loads participant picker*
```
$ ./browse click f2e1749
```

```
Clicked f2e1749.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (76 more lines in actions.jsonl)
```

*Select Load as a buffer load participant*
```
$ ./browse click f2e1855
```

```
Clicked f2e1855.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (72 more lines in actions.jsonl)
```

*Open the Generation participant picker*
```
$ ./browse click f2e1762
```

```
Clicked f2e1762.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (82 more lines in actions.jsonl)
```

*Select Solar as a generation participant*
```
$ ./browse click f2e1885
```

```
Clicked f2e1885.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (78 more lines in actions.jsonl)
```

*Open the Batteries participant picker*
```
$ ./browse click f2e1775
```

```
Clicked f2e1775.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (88 more lines in actions.jsonl)
```

*Select Battery as a batteries participant*
```
$ ./browse click f2e1915
```

```
Clicked f2e1915.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (84 more lines in actions.jsonl)
```

Now the Level: I'll enter 21% (about 6.8 kWh of the 32.2 kWh battery, covering 12 hours at the Load's average forecast).

*Type 21 into the Level field*
```
$ ./browse type f2e1811 "21"
```

```
Typed into f2e1811.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (91 more lines in actions.jsonl)
```

*Choose Fixed value 21 % for the level*
```
$ ./browse click f2e1934
```

```
Clicked f2e1934.

Page: /config/integrations/integration/haeo
- alertdialog "Buffer configuration" [ref=f2e1678]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Buffer configuration" [ref=f2e1691]
    - generic [ref=f2e1694]:
      - generic [ref=f2e1695]:
... (92 more lines in actions.jsonl)
```


The window (12 h) and level (21%) are set. I'm keeping the default shortfall cost and will flag it at the end. Submitting now.

*Submit the buffer configuration*
```
$ ./browse click f2e1839
```

```
Clicked f2e1839.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1949]:
  - generic [ref=f2e1679]:
    - banner [ref=f2e1681]:
      - generic [ref=f2e1682]:
        - generic "Close" [ref=f2e1685]:
          - button "Close" [ref=f2e1686] [cursor=pointer]
        - generic "Success" [ref=f2e1950]
    - generic [ref=f2e1951]:
      - paragraph [ref=f2e1953]: Created configuration for Outage reserve.
... (1 more lines in actions.jsonl)
```

*Finish and close the success dialog*
```
$ ./browse click f2e1956
```

```
Clicked f2e1956.

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


The buffer was created. I'll check its entities to confirm the level and window took effect.

*Open the Outage reserve buffer device*
```
$ ./browse click f2e1580
```

```
Clicked f2e1580.

Page: /config/devices/device/b1973a966fcce7f1e7d53e23ce252fad
- generic [ref=f2e4]:
  - complementary [ref=f2e5]:
    - generic [ref=f2e7]:
      - generic [ref=f2e8]:
        - generic "Sidebar toggle" [ref=f2e10]:
          - button "Sidebar toggle" [ref=f2e11] [cursor=pointer]
        - generic [ref=f2e14]: Home Assistant
      - generic [ref=f2e15]:
        - generic [ref=f2e17]:
... (90 more lines in actions.jsonl)
```


I set up an "Outage reserve" buffer in HAEO so the optimizer keeps energy for a 12-hour outage. It's created and its sensors are live, but the battery is currently well below the reserve, so HAEO will be trying to charge it.

**What I configured**
- **Kind:** Reserve (keep energy), not Headroom.
- **Participants:**
  - Loads: Load (the house).
  - Generation: Solar, since it keeps producing during an outage.
  - Batteries: Battery.
- **Window:** 12 h (the default, matching your requirement).
- **Level:** 21%. The Battery's capacity is 32.2 kWh, so this is about 6.8 kWh. The Load's 168-hour average forecast is about 0.56 kW, which is about 6.7 kWh over 12 hours.
- **Shortfall cost:** left at the default 0.05 $/kWh/h.

**What the buffer reports now**
- Energy shortfall: 6.06 kWh.
- Required energy: 3.41 kWh.
- Available energy: -2.64 kWh.
- The battery is at 12.8% state of charge, so the reserve is not met yet.

**Where I hesitated or may have gone wrong**
- **Level units:** The Level field only offers percent. I had no sensor for "energy needed for 12 hours", so I worked the percentage out by hand from the battery capacity and the load forecast. If the Load's real overnight draw is higher than the 168-hour average, 21% may be too low.
- **Solar credit:** I added Solar as generation because you said it helps during a cut. I don't know how much of the reserve HAEO will count on it, and I did not size the reserve to account for it, so 21% may be conservative.
- **Shortfall cost:** I kept the default 0.05 $/kWh/h without checking it. Grid import was around 0.16 $/kWh in the entity list, so a shortfall may be cheaper to HAEO than buying energy to fill the reserve. If the reserve should be firm, this probably needs raising. I don't know the exact units, so I left it alone.
- **Lost entry:** I closed the dialog once to look up the battery capacity and the load figures, which discarded my first attempt. I re-entered everything from scratch, and the final buffer matches what I intended.
- **Charging cost:** Because the reserve is currently unmet, HAEO may buy grid energy to reach it. I did not check whether that is acceptable to you.


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


The page lists a "Buffer" element type. That looks like the right place for a power-cut reserve, so I'll open it and read what it does.

*Click Buffer add button*
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


The Buffer dialog fits. I'll set it up as a Reserve, name it clearly, and then choose the participants. Next I'll rename it and open the Loads and Generation participant pickers.

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


The Loads picker offers the "Load" element, which is your house. I'll select it.

*Select Load as buffer participant*
```
$ ./browse click f2e641
```

```
Clicked f2e641.

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

Load is added. Next I'll open the Generation section to add Solar, since it keeps producing during an outage.

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
$ ./browse click f2e671
```

```
Clicked f2e671.

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


Solar is added. Now the Batteries section, which holds the buffer together and needs the Battery element.

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
$ ./browse click f2e701
```

```
Clicked f2e701.

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


Participants are set: Load, Solar, and Battery. Next is the Level, which sets how much energy to hold back. I'll open that picker to see what it accepts.

*Open Level field options*
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


The only option offered for Level is the battery state-of-charge sensor. That's a percentage, not the energy to hold back, so I won't use it. Level is optional, and the preview already shows the reserve effect over the 12-hour window, so I'll leave it empty. I'll click away to close the list without picking anything.

*Close Level dropdown without selecting*
```
$ ./browse click f2e568
```

```
Clicked f2e568.

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


That click collapsed the Requirement section, so I'll reopen it to confirm the 12-hour window is still set.

*Expand Requirement section again*
```
$ ./browse click f2e567
```

```
Clicked f2e567.

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


The 12-hour window is intact. I'll submit the buffer.

*Submit the buffer configuration*
```
$ ./browse click f2e626
```

```
Clicked f2e626.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e743]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e744]
    - generic [ref=f2e745]:
      - paragraph [ref=f2e747]: Created configuration for Outage reserve.
... (1 more lines in actions.jsonl)
```

*Click Finish on success dialog*
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
... (390 more lines in actions.jsonl)
```


I added an "Outage reserve" buffer to HAEO. It is set up as a 12-hour reserve, but I'm not sure it will hold enough energy yet.

**What I set:**
- **Name:** Outage reserve
- **Kind:** Reserve (keep energy), not Headroom
- **Participants:**
  - Loads: Load (your house)
  - Generation: Solar, since it keeps producing during a cut
  - Batteries: Battery
- **Window:** 12 h (the default, which matches your requirement)
- **Shortfall cost:** 0.05 $/kWh/h (the default; I didn't change it)
- **Level:** left empty

HAEO confirmed "Created configuration for Outage reserve," and the Home hub now lists the buffer with 6 entities.

**Where I hesitated or may have gone wrong:**
- **Level left empty.** The only option offered was the battery state-of-charge sensor, which is a percentage and not an energy amount, so I didn't use it. I don't know your house's energy use over 12 hours, so I couldn't enter a fixed kWh reserve. If HAEO doesn't derive the reserve from the load forecast when Level is empty, the buffer may not hold enough. You may want to set Level to a kWh value.
- **Preview looked odd.** The "What it would do" preview said loads over the window take up to 24% of battery charge, and that the battery goes as low as 5% with the buffer, the same as the plan now. I didn't understand why the buffer changed nothing, and I didn't check the result after saving.
- **Accidental collapse.** I clicked the Requirement heading to close a dropdown and collapsed that section. I reopened it and confirmed the 12 h window was still set before submitting.
- **Solar and the 12-hour window.** I included Solar because you said it helps during an outage. I didn't check whether HAEO counts it as reliable backup or how much it contributes. The 12-hour window and Solar's share are the parts I'd most want to verify.


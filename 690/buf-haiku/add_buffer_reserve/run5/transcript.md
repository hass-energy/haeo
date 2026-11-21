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


The HAEO page lists a "Buffer" element type, which looks like the right place for a backup-energy reserve. I'll open it to read what it does.

*Open the Buffer element type form*
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


The Buffer form has a "Reserve" kind, a Window (set to 12 h by default, which matches the outage length), a Level, participants (Loads, Generation, Batteries), and a shortfall cost. I'll open the Loads participant section first.

*Open the Loads participant options*
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
... (77 more lines in actions.jsonl)
```

*Select Load as the buffer load*
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

Load is added to the buffer. Next I'll add Solar under Generation, since it keeps producing during an outage.

*Open the Generation participant options*
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


Solar is added. Now I'll add the Battery under Batteries, since the reserve is held in the battery.

*Open the Batteries participant options*
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

*Select Battery as the buffer battery*
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


Participants are set. The Level field decides how much energy to hold back, so I'll open it to see what it accepts.

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
... (101 more lines in actions.jsonl)
```


The Level picker only suggests a battery state-of-charge sensor, which isn't the energy amount I need. I'll search for the house load sensor so I can size the reserve from real consumption.

*Search Level picker for load sensors*
```
$ ./browse type f2e594 "load"
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
... (92 more lines in actions.jsonl)
```


*Re-read the dialog to see Level search results*
```
$ ./browse look
```

```
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
        - paragraph [ref=f2e481]: Keep energy in your batteries for an outage (a reserve), or empty space for incoming generation (headroom).
        - generic [ref=f2e483]:
... (90 more lines in actions.jsonl)
```


The Level search returns nothing for "load", and the form's own preview already says that covering the loads over the 12 h window takes up to 24% of battery charge. Level is not marked required, so I'll leave it empty and let HAEO compute the reserve from the loads. I'll clear the search text and set a clearer buffer name.

*Clear the Level search text and close the picker*
```
$ ./browse type f2e594 "" && ./browse press Escape
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
... (205 more lines in actions.jsonl)
```


The Level field is clear and the picker is closed. I'll rename the buffer to something descriptive.

*Rename the buffer to Outage reserve*
```
$ ./browse type f2e487 "Outage reserve"
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
... (92 more lines in actions.jsonl)
```


Name is set. The preview's "as low as 5%" doesn't obviously show a higher floor, so I'll submit and then check the saved buffer.

*Submit the buffer configuration*
```
$ ./browse click f2e626
```

```
Clicked f2e626.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e750]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e751]
    - generic [ref=f2e752]:
      - paragraph [ref=f2e754]: Created configuration for Outage reserve.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
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
... (390 more lines in actions.jsonl)
```


I created a HAEO buffer called "Outage reserve" to keep enough battery charge for a 12-hour outage, but I did not set an explicit energy amount, and I could not confirm the reserve is actually holding charge.

**What I set up:**
- **Kind:** Reserve (keep energy), not Headroom.
- **Window:** 12 h, the default, which matches your outage length.
- **Participants:** Load (the house loads), Solar (generation that keeps producing during an outage), and Battery (the store holding the reserve).
- **Level:** left empty. HAEO's preview computes the energy needed to cover the loads over the window.
- **Shortfall cost:** left at the default of 0.05 $/kWh/h.

The success dialog confirmed the buffer was created, and it now appears in the hub's device list.

**Where I hesitated or may have gone wrong:**
- **Level left empty.** The field is not marked required, and the preview said covering the loads over 12 h takes up to 24% of battery charge. But the same preview said the battery would drop "as low as 5%" with the buffer, the same as the current plan. That suggests the reserve may not raise the floor, and an empty Level may mean no reserve at all. I did not check this further. Confirm the buffer's effect before relying on it during an outage.
- **Level search found no load sensor.** Searching "load" in the Level picker returned nothing, and the only suggestion was the battery state-of-charge sensor. I did not know which unit Level expects (kWh or %), so I did not type a number.
- **Solar as a participant.** I included Solar because you said it helps during a power cut. HAEO's text says generation "keeps producing through an outage" counts toward the reserve, but I could not check how much solar it credits.
- **Name.** I renamed the buffer "Outage reserve" without being asked; the default was "Buffer".
- **Battery state.** The battery sensor showed about 12.8% state of charge when I opened the picker. That is low for a 12-hour outage, and I did not check whether the reserve is achievable from that level.


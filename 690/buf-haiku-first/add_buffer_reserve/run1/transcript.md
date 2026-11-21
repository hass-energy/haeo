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


The home hub has Grid, Load, Inverter, Solar, Battery and Switchboard. There is a "Buffer" element type, which looks like the right place for a reserve. I'll open it to see what it does.

*Click Buffer element type button*
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


The Buffer form has the right kind, "Reserve: keep energy", selected by default, and the 12 h window is already filled in. Next I'll look at the participant choices and the "What it would do" text.

*Expand 'What it would do' section*
```
$ ./browse click f2e620
```

```
Clicked f2e620.

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


*Click Loads participant button*
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

*Select Load option*
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

Load is added as a participant. Next I'll add Generation (Solar) and Batteries.

*Click Generation participant button*
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

*Select Solar option*
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

*Click Batteries participant button*
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

*Select Battery option*
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


Load, Solar and Battery are now participants. Next is the Level field, which sets how much energy to hold back. I'll open it to see what it accepts.

*Open Level field to see options*
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


The Level picker is showing only the battery state-of-charge sensor. I'll type "load" to see whether a household consumption sensor is available to base the reserve on.

*Search Level field for load sensors*
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


*Stop and report that the reserve level value is missing*
```
$ ./browse giveup "Buffer is set up as a Reserve over a 12 h window with Load, Solar and Battery as participants, but I stopped before submitting. The Level field needs the energy to hold back for 12 hours of house use (in kWh or as a percentage of battery), and I don't have that figure. The Level search returned no load-consumption sensor, only the battery state-of-charge sensor. Nothing was submitted."
```

```
Recorded. You can stop now.
```

I haven't submitted the buffer. It needs one number I don't have: how much energy the house uses in 12 hours.

**What's set up in the open Buffer form (not submitted):**
- Name: "Buffer" (default, unchanged)
- Kind: "Reserve: keep energy", which is the right choice for a power-cut reserve. Headroom is the other option and doesn't apply here.
- Participants: Load (loads to keep running), Solar (generation that keeps producing through an outage, so it counts toward the reserve), and Battery (holds the buffer together).
- Window: 12 h, already filled in by default and matching your requirement.
- Shortfall cost: 0.05 $/kWh/h, the default, which I left alone.

**What's missing:** the Level field. It's the amount of energy to keep in the batteries. The only sensor the Level search offered was the battery state-of-charge sensor, and I couldn't find a load-consumption sensor. Without a 12-hour usage figure, any number I entered would be a guess. The preview also showed "Keeps up to 24% charge", which didn't match anything I had entered, so I couldn't tell what the field expects.

**What I need from you:** your household's average consumption for 12 hours, in kWh. If you'd rather give the reserve as a battery percentage, tell me your battery's usable capacity too. Then I can set the Level and submit.

**Points where I hesitated or was unsure:**
- The Level field's unit (kWh or %) was not clear from the page, and the preview's 24% figure didn't match anything I'd entered.
- I didn't know the household's load, so I couldn't size the reserve. I didn't want to submit a made-up value.
- I added Solar as a participant because you said it keeps producing during an outage. I didn't check whether counting it could leave the reserve too small if your panels produce little in bad weather. You may want to size the reserve without solar as a safety margin.
- My first click on "What it would do" did nothing, so I expanded the Loads picker instead. That was harmless, but it's a small misstep.
- I gave up with `giveup` after the Level search came back empty. That was a judgement call: the task is blocked on your number, not on the interface.


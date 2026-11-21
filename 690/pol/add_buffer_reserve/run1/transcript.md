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
... (350 more lines in actions.jsonl)
```

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

Window already 12 h. Fill participants.

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

```
$ ./browse click f2e637
```

```
Clicked f2e637.

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

```
$ ./browse click f2e667; ./browse click f2e558
```

```
Clicked f2e667.

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
... (178 more lines in actions.jsonl)
```


```
$ ./browse click f2e697 >/dev/null; ./browse click f2e594
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


```
$ ./browse press Escape >/dev/null; ./browse look | grep -E "alertdialog|Submit|Level"
```

```
- alertdialog "Buffer configuration" [ref=f2e461]:
                  - generic [ref=f2e592]: Level
                  - 'combobox "Level: search entities or enter a value" [ref=f2e594]'
      - button "Submit" [ref=f2e622] [cursor=pointer]
```

I've filled in the Buffer form, and I'm about to submit it.

```
$ ./browse click f2e622
```

```
Clicked f2e622.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e724]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e725]
    - generic [ref=f2e726]:
      - paragraph [ref=f2e728]: Created configuration for Buffer.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e731 | grep -i -B2 -A8 buffer | head -30
```

```
          - button "EV" [ref=f2e123] [cursor=pointer]
          - button "Policy" [ref=f2e126] [cursor=pointer]
          - button "Buffer" [ref=f2e129] [cursor=pointer]
      - generic [ref=f2e131]:
        - heading "Hubs" [level=3] [ref=f2e132]
        - generic [ref=f2e134]:
          - generic:
            - listitem [ref=f2e136]:
              - generic [ref=f2e137]:
                - button [ref=f2e140] [cursor=pointer]
                - generic [ref=f2e143]: Home
--
... (18 more lines in actions.jsonl)
```

```
$ ./browse done "Created a Reserve-type Buffer in Home: participants Load, Solar (generation), Battery; window 12 h; level left blank; shortfall cost left at default 0.05 \$/kWh/h."
```

```
Recorded. You can stop now.
```

I added a Buffer to your Home setup so HAEO keeps enough energy in the battery to cover a 12-hour power cut. HAEO showed "Created configuration for Buffer", and the new Buffer is listed under Home. I didn't check that the optimizer now holds a reserve in practice.

- **Kind:** Reserve (keep energy).
- **Load:** your Load.
- **Generation:** Solar, so it counts toward covering the outage.
- **Battery:** your Battery.
- **Window:** 12 hours. The form already had this as its default and I left it.

Points where I hesitated or left things to defaults:
- **Level:** I left it empty. It is optional and I couldn't tell what an empty value means. I assumed it means "cover the full window", but I didn't confirm that. The only suggestion offered was the battery state-of-charge sensor, which didn't seem right for this.
- **Shortfall cost:** I left it at the default of 0.05 $/kWh/h. I don't know whether that is high enough to make HAEO reliably hold the reserve, and I didn't change it.
- **Switchboard and Grid:** I didn't add them as participants. The form only offered Load, Solar and Battery, and those seemed to be the right ones.


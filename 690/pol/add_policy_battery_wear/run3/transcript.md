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

Use the Policy element.

```
$ ./browse click f2e126
```

```
Clicked f2e126.

Page: /config/integrations/integration/haeo
- alertdialog "Policies" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Policies" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (28 more lines in actions.jsonl)
```


```
$ ./browse type f2e491 Battery wear; ./browse click f2e499
```

```
$ ./browse look | grep -n -i -E "combobox|option" | head
```

```
Typed into f2e491.

Page: /config/integrations/integration/haeo
- alertdialog "Policies" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Policies" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (68 more lines in actions.jsonl)
```

```
22:                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
23:                  - option "+" [selected]
24:                  - option "🏭 Grid"
25:                  - option "🔋 Battery"
26:                  - option "☀️ Solar"
29:                - combobox "Add an element to To" [ref=f2e506] [cursor=pointer]:
30:                  - option "+" [selected]
31:                  - option "🏭 Grid"
32:                  - option "🔋 Battery"
33:                  - option "🏠 Load"
```

Try typing the option into the select.

```
$ ./browse type f2e499 "🔋 Battery" | head -30
```

```
Error: Locator.fill: Error: Element is not an <input>, <textarea> or [contenteditable] element

Page: /config/integrations/integration/haeo
- alertdialog "Policies" [ref=f2e461]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Policies" [ref=f2e474]
    - generic [ref=f2e477]:
      - generic [ref=f2e478]:
... (18 more lines in actions.jsonl)
```

Native select; use keyboard.

```
$ ./browse press ArrowDown | head -3; ./browse press ArrowDown | head -3; ./browse press Enter | sed -n 15,35p
```

```
Pressed ArrowDown.

Page: /config/integrations/integration/haeo
Pressed ArrowDown.

Page: /config/integrations/integration/haeo
          - generic [ref=f2e487]: Rules *
          - generic [ref=f2e488]:
            - generic [ref=f2e489]:
              - switch "Battery wear on" [checked] [ref=f2e519] [cursor=pointer]
              - textbox "Rule name" [ref=f2e491]: Battery wear
              - generic [ref=f2e522]:
... (15 more lines in actions.jsonl)
```

Battery is in From. Now price 0.01.

```
$ ./browse type f2e521 0.01 | sed -n 30,60p
```

```
                  - button "Remove Battery" [ref=f2e528] [cursor=pointer]
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🏭 Grid"
                  - option "☀️ Solar"
              - group "To" [ref=f2e503]:
                - generic [ref=f2e505]: Any
                - combobox "Add an element to To" [ref=f2e506] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🏭 Grid"
                  - option "🔋 Battery"
                  - option "🏠 Load"
... (12 more lines in actions.jsonl)
```

```
$ ./browse click f2e533 | sed -n 14,60p
```

```
        - generic [ref=f2e486]:
          - generic [ref=f2e487]: Rules *
          - generic [ref=f2e488]:
            - generic [ref=f2e489]:
              - switch "Battery wear on" [checked] [ref=f2e519] [cursor=pointer]
              - textbox "Rule name" [ref=f2e491]: Battery wear
              - generic [ref=f2e522]:
                - generic [aria-hidden] [ref=f2e523]: 🔋
                - text: Battery
              - button "Remove Battery wear" [ref=f2e520] [cursor=pointer]
            - generic [ref=f2e495]:
              - group "From" [ref=f2e496]:
... (29 more lines in actions.jsonl)
```

```
$ ./browse click f2e516 | head -30
```

```
Clicked f2e516.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e548]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e549]
    - generic [ref=f2e550]:
      - paragraph [ref=f2e552]: Created configuration for Policies.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e555 | head -5; ./browse done "Added a Policy with rule 'Battery wear': From Battery, To Any, price fixed 0.01 \$/kWh."
```

```
Clicked f2e555.

Page: /config/integrations/integration/haeo
- generic [ref=f2e4]:
  - complementary [ref=f2e5]:
Recorded. You can stop now.
```

I added a Policy to HAEO with one rule, "Battery wear". It charges a fixed 0.01 $/kWh on power flowing from the Battery to anywhere. HAEO showed "Created configuration for Policies", and I clicked Finish. I didn't reopen the Policy afterwards to confirm the saved rule.

I left "To" empty, which the dialog says means the rule applies to every element on that side.

Points where I hesitated or slipped:
- **Element picker:** the "From" picker is a native dropdown. My first attempt to type into it failed, so I selected Battery with the keyboard instead. Battery then showed as a chip under "From".
- **Price entry:** typing 0.01 only offered a "Fixed value 0.01 $/kWh" suggestion, so I clicked it to confirm. I assumed $/kWh was the right unit for "1 cent per kWh".
- **Rule name:** the dialog suggested "Rule 1". I renamed it to "Battery wear" so it's recognisable later.


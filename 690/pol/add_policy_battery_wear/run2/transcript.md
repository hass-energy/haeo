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
$ ./browse type f2e491 "Battery wear"; ./browse click f2e499; ./browse press ArrowDown; 
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
... (108 more lines in actions.jsonl)
```


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

Try keyboard selection: focused select, ArrowDown twice.

```
$ ./browse press ArrowDown | grep -A8 'group "From"'; ./browse press ArrowDown | grep -A8 'group "From"'; ./browse press Enter | grep -A8 'group "From"'
```

```
              - group "From" [ref=f2e496]:
                - generic [ref=f2e498]: Any
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🏭 Grid"
                  - option "🔋 Battery"
                  - option "☀️ Solar"
              - group "To" [ref=f2e503]:
                - generic [ref=f2e505]: Any
              - group "From" [ref=f2e496]:
                - generic [ref=f2e498]: Any
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
... (15 more lines in actions.jsonl)
```

Wrong one (Solar). Remove it and retry.

```
$ ./browse click f2e526 >/dev/null; ./browse click f2e499 >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press Enter | grep -A12 'group "From"'
```

```
              - group "From" [ref=f2e496]:
                - generic [ref=f2e530]:
                  - generic [ref=f2e531]:
                    - generic [aria-hidden] [ref=f2e532]: 🏭
                    - generic [ref=f2e533]: Grid
                  - button "Remove Grid" [ref=f2e534] [cursor=pointer]
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🔋 Battery"
                  - option "☀️ Solar"
              - group "To" [ref=f2e503]:
                - generic [ref=f2e505]: Any
... (1 more lines in actions.jsonl)
```


```
$ ./browse click f2e534 >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press Enter | grep -A8 'group "From"'
```

```
              - group "From" [ref=f2e496]:
                - generic [ref=f2e537]: Any
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🏭 Grid"
                  - option "🔋 Battery"
                  - option "☀️ Solar"
              - group "To" [ref=f2e503]:
                - generic [ref=f2e505]: Any
```

```
$ ./browse click f2e499 >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press Enter | grep -A8 'group "From"'
```

```
              - group "From" [ref=f2e496]:
                - generic [ref=f2e540]:
                  - generic [ref=f2e541]:
                    - generic [aria-hidden] [ref=f2e542]: 🔋
                    - generic [ref=f2e543]: Battery
                  - button "Remove Battery" [ref=f2e544] [cursor=pointer]
                - combobox "Add an element to From" [ref=f2e499] [cursor=pointer]:
                  - option "+" [selected]
                  - option "🏭 Grid"
```

Now the price.

```
$ ./browse type f2e521 0.01 | grep -B3 -A12 'Price'
```

```
                  - option "🔋 Battery"
                  - option "🏠 Load"
            - generic [ref=f2e507]:
              - generic [ref=f2e508]: Battery wear Price *
              - 'combobox "Battery wear Price: search entities or enter a value" [expanded] [ref=f2e521]': "0.01"
              - listbox [ref=f2e547]:
                - group [ref=f2e548]:
                  - option "Fixed value 0.01 $/kWh" [ref=f2e549] [cursor=pointer]:
                    - generic [aria-hidden] [ref=f2e550]:
                      - generic [ref=f2e551]: "0.01"
                      - generic [ref=f2e552]: $/kWh
                    - generic [ref=f2e553]: Fixed value
... (2 more lines in actions.jsonl)
```

```
$ ./browse click f2e549 >/dev/null; ./browse look | grep -A40 'Rules'
```

```
          - generic [ref=f2e487]: Rules *
          - generic [ref=f2e488]:
            - generic [ref=f2e489]:
              - switch "Battery wear on" [checked] [ref=f2e519] [cursor=pointer]
              - textbox "Rule name" [ref=f2e491]: Battery wear
              - generic [ref=f2e538]:
                - generic [aria-hidden] [ref=f2e539]: 🔋
                - text: Battery
              - button "Remove Battery wear" [ref=f2e520] [cursor=pointer]
            - generic [ref=f2e495]:
              - group "From" [ref=f2e496]:
                - generic [ref=f2e540]:
... (28 more lines in actions.jsonl)
```


```
$ ./browse click f2e516 | head -40
```

```
Clicked f2e516.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e564]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e565]
    - generic [ref=f2e566]:
      - paragraph [ref=f2e568]: Created configuration for Policies.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e571 >/dev/null; ./browse done "Added a Policy with rule 'Battery wear': from Battery, to Any, price fixed 0.01 \$/kWh."
```

```
Recorded. You can stop now.
```

HAEO now has a Policy with one rule, "Battery wear". The rule charges a fixed $0.01/kWh on energy flowing from Battery to Any, so it applies wherever the discharged energy goes. The dialog said "Created configuration for Policies." I didn't reopen the Policy afterwards to check that the rule saved as entered.

Points where I hesitated or made mistakes:
- **Element picker:** The "From" picker is a plain dropdown, and typing into it failed. I picked items with the keyboard and twice added the wrong element (Solar, then Grid). I removed each one and re-added Battery. The form showed only Battery in "From" when I submitted.
- **"To" side:** I left it as "Any" so the charge covers every destination. I wasn't sure whether "Any" includes the Switchboard, Inverter and similar parts.
- **Price units:** I assumed the price field means $/kWh. The "Fixed value 0.01 $/kWh" option confirmed it.
- **Rule name:** The form asked for no policy name, so I renamed the default "Rule 1" to "Battery wear".


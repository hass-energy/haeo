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

Use the Policy button.

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
$ ./browse type f2e491 Battery wear; ./browse click f2e499 ; ./browse look | grep -n -i -E "combobox|option" | head
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
... (78 more lines in actions.jsonl)
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

Try keyboard on the focused select.

```
$ ./browse click f2e499 >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press ArrowDown >/dev/null; ./browse press Enter | sed -n 18,40p
```

```
            - generic [ref=f2e553]: Rules *
            - generic [ref=f2e554]:
              - generic [ref=f2e555]:
                - switch "Battery wear on" [checked] [ref=f2e556] [cursor=pointer]
                - textbox "Rule name" [ref=f2e557]: Battery wear
                - button "Remove Battery wear" [ref=f2e558] [cursor=pointer]
              - generic [ref=f2e561]:
                - group "From" [ref=f2e562]:
                  - generic [ref=f2e564]:
                    - generic [ref=f2e565]:
                      - generic [aria-hidden] [ref=f2e566]: 🏭
                      - generic [ref=f2e567]: Grid
... (11 more lines in actions.jsonl)
```

Both Grid and Battery got added; remove Grid.

```
$ ./browse click f2e568 | sed -n 18,50p
```

```
            - generic [ref=f2e553]: Rules *
            - generic [ref=f2e554]:
              - generic [ref=f2e555]:
                - switch "Battery wear on" [checked] [ref=f2e556] [cursor=pointer]
                - textbox "Rule name" [ref=f2e557]: Battery wear
                - generic [ref=f2e597]:
                  - generic [aria-hidden] [ref=f2e598]: 🔋
                  - text: Battery
                - button "Remove Battery wear" [ref=f2e558] [cursor=pointer]
              - generic [ref=f2e561]:
                - group "From" [ref=f2e562]:
                  - generic [ref=f2e571]:
... (20 more lines in actions.jsonl)
```

```
$ ./browse type f2e589 0.01 | sed -n 40,60p; ./browse screenshot
```

```
                  - combobox "Add an element to To" [ref=f2e585] [cursor=pointer]:
                    - option "+" [selected]
                    - option "🏭 Grid"
                    - option "🔋 Battery"
                    - option "🏠 Load"
              - generic [ref=f2e586]:
                - generic [ref=f2e587]: Battery wear Price *
                - 'combobox "Battery wear Price: search entities or enter a value" [expanded] [ref=f2e589]': "0.01"
                - listbox [ref=f2e599]:
                  - group [ref=f2e600]:
                    - option "Fixed value 0.01 $/kWh" [ref=f2e601] [cursor=pointer]:
                      - generic [aria-hidden] [ref=f2e602]:
... (6 more lines in actions.jsonl)
```

```
$ ./browse click f2e601 | sed -n 44,60p
```

```
                    - option "🏠 Load"
              - generic [ref=f2e586]:
                - generic [ref=f2e587]: Battery wear Price *
                - generic [ref=f2e588]:
                  - generic [ref=f2e607]:
                    - button "Fixed value 0.01 $/kWh" [ref=f2e608] [cursor=pointer]:
                      - generic [aria-hidden] [ref=f2e609]:
                        - generic [ref=f2e610]: "0.01"
                        - generic [ref=f2e611]: $/kWh
                      - generic [ref=f2e612]: Fixed value
                    - button "Remove 0.01 $/kWh" [ref=f2e613] [cursor=pointer]
                  - 'combobox "Battery wear Price: search entities or enter a value" [ref=f2e589]'
... (2 more lines in actions.jsonl)
```

```
$ ./browse click f2e595 | head -40
```

```
Clicked f2e595.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e616]:
  - generic [ref=f2e462]:
    - banner [ref=f2e464]:
      - generic [ref=f2e465]:
        - generic "Close" [ref=f2e468]:
          - button "Close" [ref=f2e469] [cursor=pointer]
        - generic "Success" [ref=f2e617]
    - generic [ref=f2e618]:
      - paragraph [ref=f2e620]: Created configuration for Policies.
... (1 more lines in actions.jsonl)
```

```
$ ./browse click f2e623 >/dev/null; ./browse done "Created a Policy rule 'Battery wear': From Battery, To Any, price fixed 0.01 \$/kWh. Saved successfully."
```

```
Recorded. You can stop now.
```

I added a Policy rule called "Battery wear". It charges $0.01 per kWh on any energy leaving the Battery. Home Assistant showed "Created configuration for Policies." and I clicked Finish. I didn't reopen the Policy to check it afterwards.

- **From:** Battery.
- **To:** left as Any, so the charge applies wherever the discharged energy goes.
- **Price:** a fixed value of 0.01 $/kWh.

Points where I hesitated or made a mistake:
- **Extra Grid element:** The element dropdown was a plain select, so I used the keyboard to pick Battery. That added Grid and Battery together. I removed Grid before submitting.
- **"Any" on the To side:** The To list offered Grid, Battery and Load but not Inverter or Solar. I assumed "Any" covers every destination, as the help text says, but I couldn't check that.
- **Price entry:** Typing 0.01 did nothing until I selected the "Fixed value 0.01 $/kWh" suggestion that appeared.


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
... (312 more lines in actions.jsonl)
```


*Click Solar to add a solar element*
```
$ ./browse click f2e114
```

```
Clicked f2e114.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (39 more lines in actions.jsonl)
```


The solar dialog is open. Your panels feed the inverter, so the default "Inverter, DC" connection is right. Next I'll look at the forecast picker.

*Open the forecast entity picker*
```
$ ./browse click f2e485
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (241 more lines in actions.jsonl)
```


The picker lists 32 Forecast.Solar sensors: today, tomorrow, day after tomorrow, and 3 to 7 days out, for each of East, North, South and West. The Sigen sensors are not forecast sensors for the panels, so I'll leave them out. I'll select the first East option to see how multi-select behaves.

*Select the East 3-days-from-now forecast sensor*
```
$ ./browse click f2e499
```

```
Clicked f2e499.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (50 more lines in actions.jsonl)
```


Multi-select works, and the picker closes after each choice. I'll filter by the exact entity ID and confirm with Enter, starting with the East tomorrow sensor.

*Filter picker by East tomorrow sensor and select it*
```
$ ./browse click f2e485 && ./browse type f2e485 "sensor.energy_production_tomorrow_east" && ./browse press Enter
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (181 more lines in actions.jsonl)
```


The filter-and-Enter method works, and the combobox ref stays the same. I'll add the remaining East sensors.

*Add remaining East forecast sensors and take screenshot*
```
$ for s in energy_production_today_east energy_production_d2_east energy_production_d3_east energy_production_d4_east energy_production_d5_east energy_production_d6_east energy_production_d7_east; do :; done; ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_today_east" >/dev/null && ./browse press Enter >/dev/null && ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_d2_east" >/dev/null && ./browse press Enter >/dev/null && ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_d4_east" >/dev/null && ./browse press Enter >/dev/null && ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_d5_east" >/dev/null && ./browse press Enter >/dev/null && ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_d6_east" >/dev/null && ./browse press Enter >/dev/null && ./browse click f2e485 >/dev/null && ./browse type f2e485 "sensor.energy_production_d7_east" >/dev/null && ./browse press Enter >/dev/null && ./browse screenshot
```

```
Permission to use Bash has been denied because Claude Code is running in don't ask mode. IMPORTANT: You *may* attempt to accomplish this action using other tools that might naturally be used to accomplish this goal, e.g. using head instead of cat. But you *should not* attempt to work around this denial in malicious ways, e.g. do not use your ability to run tests to execute non-test actions. You should only try to work around this restriction in reasonable ways that do not attempt to bypass the intent behind this denial. If you believe this capability is essential to complete the user's request, STOP and explain to the user what you were trying to do and why you need this permission. Let the user decide how to proceed.
```


*Check current form state after denied command*
```
$ ./browse look
```

```
Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
        - paragraph [ref=f2e436]: Configure solar forecasting and parameters
        - generic [ref=f2e438]:
... (53 more lines in actions.jsonl)
```


The denial applied only to that long chained command; single browse calls still work, so I'll continue one step at a time.

*Open the forecast picker*
```
$ ./browse click f2e485
```

```
Clicked f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (55 more lines in actions.jsonl)
```

*Type the East today sensor ID into the picker*
```
$ ./browse type f2e485 "sensor.energy_production_today_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (57 more lines in actions.jsonl)
```

*Confirm the highlighted East today sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (60 more lines in actions.jsonl)
```


Confirmed: the East today sensor is added. Next I'll test whether the combobox keeps focus so I can type straight into it.

*Type the East day-after-tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d2_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (62 more lines in actions.jsonl)
```


Typing directly into the combobox works, so each sensor takes two steps: type, then Enter.

*Confirm East day-after-tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (65 more lines in actions.jsonl)
```

*Type the East 3-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d3_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (60 more lines in actions.jsonl)
```


*Confirm East 3-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (60 more lines in actions.jsonl)
```


The Enter press did not select anything; the dropdown was not showing. I'll retype the ID to bring up the matches.

*Retype the East 3-days filter to show matches*
```
$ ./browse type f2e485 "energy_production_d3_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (60 more lines in actions.jsonl)
```


*Take screenshot of the solar dialog*
```
$ ./browse screenshot
```

```
Saved /home/codespace/haeo/.claude/worktrees/bridge-cse_012KWZvNQZAmMAZDSSPbhx7H/.ux-bench/why-haiku/add_solar_forecast_solar/run3/agent/screenshot-1.png
```

```
$ /home/codespace/haeo/.claude/worktrees/bridge-cse_012KWZvNQZAmMAZDSSPbhx7H/.ux-bench/why-haiku/add_solar_forecast_solar/run3/agent/screenshot-1.png
```

```
[{"type": "image", "source": {"type": "base64", "data": "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Rtv1888/q1QqmpBG4y5PIj/bVFdXU8GZYu2jjz6q1+s//PDDu+6664477rCvyU033URzKCoqysrKmjFjBgMAAACXoVQqd+7caTAYoqKiuEcf0VHHtm3bsmzso3FPP5oyZQodWtCRybfffjtt2jSFQsGcFVqBbgj3AAP0QuPHj6d01+iT2akn1X7HjRvHnAAF9XfeeWfw4MErVqzw8/Ojn/bri+gs7JAhQ959913K6tR/9OjRb7zxRmVlJX0V0VCNRkPBmKLvm2++qVarv/7669LSUgrJDz/88EsvvVRQUEBRlptPeXk59afQu3z58sLCQqrufvrpp3369HniiSfqpl9CEfrUqVM0h/T0dHd3dwYAAAAug4q9lH69vLwo0Lq5uVG4DQgIuP3224ODg0UikVgsDgkJ+dOf/kQ9aRC9nD59Oo1Mk9BRB4MeBRVggN4pNDS0qUFhYWGsmzz11FNcR0xMzDPPPHPixAn6IqFvGurzwAMP/O1vf7t8+XJERASzNS9BMZ46Tp486evrm5CQQN30xfPVV1/NnDmTkip9D3EnaB955JErV65IpdJnn32Wu96bJrx06RK3ILPZzOfz6VuNZvviiy86WDcabe7cuZS6qT5M3QwAAABcxsiRI8+ePUun2pOTkynilpSUSCQSOvyYPXu2fZzMzEw6506n5v39/emQg0amM+Zd365Kq6AV6IYQgAGg69S7B1ilUlEA5rqFQiEVgamQywVgu4qKiosXL86fP597yV3YTF859gkp+nIf6PS19L///S83N7fu055onpSrv/nmm7Vr106cOHHWrFn0fdbougkEAkq/zHYtNAMAAABXQschdAJ97969R48e5fpotdpdu3ZFRUVxZ+p37NhBwZgbVGLDbOfcaULmxLhWoLkOBGAOAjAAdBtvb2/u+4PZmokuKytr2JIEjUO5lKq79XpWV1fX7UMnOLds2bJkyZK+ffvu27cvOzvbPmjo0KFvvPEGVYm//fZb+va66667GAAAAMC1oqOjT58+zefz6cAjLCzsyJEj58+f5x4LTEO59Dto0CAqpdLZ9rS0NIvF0ujtZuDkcJkfAHSbYcOGFRUV7dy5k9LsV199RUXdPn36NByHsuvZs2ep+9SpU7t372a2K6iVNtRNZ2fffvttvV7v5eUVHh6u0+nOnDljv5f42LFjzz33XFVVVXBwML0U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7SGf/8UAHYIMuD8iauSwXz5goPAdtDC0X42nydnbWvr32ev3pRja1M/iuygLj28ZuPFq6WW1IzeXtqt8kZqaiuTw5ptvDhgwAM1o09tZnz17dtGiRQkJCbNnz96+fXtkZKTxdjIWWRu+Y8eOJSUl58+flwY7efIkfoC7d+9u42LYKCUlBe2Ali1bmr9lbQHat2+v0WikmpgwXFBqHAXFKyyG8fYhGEzqwBH0zMxMNCmkl9hK5R8lZctnt53tU8NHw5AnTpww7Wlt4a2tfHs3ABl1OClTtm82FleIzAYgP6IMG4dv0aKF6ayNGxjccssteInVheZsjXVyZW72oq63fMdI6RdN/3Hjxk2YMAEdNmZgBmByCs2aNcORqaKioo0bN+Ifclxc3NWrV1HvxV6xwgAd69atQ882bdrgJQbDv0qMghEFORXuj4gas19//XXPnj0eBujAS6Fg+BUxth3tKo88cvDav8/mj40OiPFTWRtmTPT1k5/XpZcI+9m1MIgiWNtffPEFfikXL168detWY5XGz8/v3Xfffe2119DwvWzQvHlzYWglZ2RkFBcXVwsM1oZHW3/s2LFz5sxBmxuJZd68edOnT5cu4LRlMeR99NFHaJofP3787bffRjPXYinM2gKgPypsL730EqqRP/74I3KUMFmHvXr1QnMZE1+6dOmnn34q9UeEGzx48JNPPolPt2/fPnRcvHhRZp3Y8tltZ/vU0BJCcx9DYs1otdoPP/zwnXfesbbw1la+tS9U5vNaY++2ZCOZzabalC2uEJkNQH5NyiySjcPHx8f37dvXOOv58+cb31KpVJgCWrEIwNbmopDNXtTblr927VopPK9Zs+bChQt6vX758uV2PdBl7969+CBYhrvuukvqg44xY8agJz6C/Lj4LEo+QZRIEhMTc/fddwcGBuJf2ZYtW4ShESUMFdQpBlIFVeq5efNmDIaB77nnHouHzJSDd4E2xwBM1GihqrB//35UL0caoAMvlVwHRnFGrVYbu20fcWNGya1Rfo+0C5UZJsLb85am/q+dyLlaZnctVObxla+88kqkCWSGqKioFStW7Ny5c8iQIWlpafhpRJaQBo6OjsYvEI4fo2TUu3fvO+64A01t9J80aRIKegMHDqz2CBxrw8PChQvxizt69Oj+/fu3atUKQajagskshrwePXr85S9/wbww2RdffNHaYNYWAGsAZUN8FgSVxx57zHSUt956KysrC8MjJEybNs3Y/5NPPkGcGzZs2MSJEwcNGiTdg9faOhE2fHa72D619957D18E2kCoxe3atWvGjBnWFt7aypf5QmU+r7C0mdm7LdlIZrMxn7LFFSKzAcivSRk2Dv/xxx8bZ41t2DTEYgeIui5KwdZmoZDNXtTblo/F2LRpkzDcPQsN98LCQszxyJEjtk+hU6dO9957r/ExTsalxUaC70V+XD4EmJxFWFhYly5d0IFki7/SaRr9+vULM0CH+N+TkKQBMHBoaKhQNt4F2pzbypUrBZFLys7Oxu5M1Ke8vDy0Vu0aBUtl7ygWIeii5CulX+n+MTj8v3HjRhz4R9OqZ8+eEyZMEHXh0qVLxnvSyDAmWxk6nQ5rDC086ZTjoqIiWx4deSivPGlH2j86R9waVcPzY66Wae/ekx7p7Tm3Y9gDbUKEbVC4MN4uqHFDgzs2NhatZAQqQeRssAEbHx2EzLx9+3ZUO6WXCKhIlUuWLLE4Fjf7eoUfHRS6w8PDbbmWBAcFahzGxh8dW6xatUoQ/VlycvLevXu7du2K44D/+c9/ysvLcXRMSrlooixfvtzHxweH4XCgUHqeHBpUQtmwzFhyYYj3Fh9/WK8caNY2QPucZ6QQNULG9JuUlGS8eyo68BLH/vEWXtZVAK5D7u7uqBIUFxdLgdPX1xfd0ltLzxeuvFJscays8ushubuV21+ZaubruWJQ9CspOc8cyfrvxSIfT6unwExsETitzR93fbSlQUZEN9zUqVPHjh2LmiT2G8uWLZszZ47Uf8eOHZ9//jmagIJuBHwd5nfwIlImBEXp8exS8wO59+rVq/v370ftF8fopQqqFIalAZCBW7durfAiMO8CbY4BmKgRwgFLYbhff7t27Uz742VVVdXWrVtN7xCjKEibBQUFAQEBCMMqlQrHWaXPAqVay4+R9Pd0T2rmH+7lYcv0o3w8/9076ovzhUfyy61N0BQWgJeuETmFuXPnIvQ+88wz2NHNnDnzzjvvRE9E3/fff3/WrFnSaY3UwJAZCgsLlX+OKBGkpaVt3LixsrIyLi4OLShheB7SunXrUg2Mg0lni4wYMeKnn346f/78t99+O3LkSONTzRSorYEgEzwFmlxX4z4FOiMjw3h/nWrS09Ojo6MVeAq0pKTk+n2qpIdbCpMToU8UNlxo7xR8/XI11zn5mYioPmRmZqL2i2OaNg7PU6DpBkKB9+DBg/jdly7XR7ht2rRpVlbWoUOHcnNzcVwejUakXzTSsGFLp9ctXboUrRRUVhMTEwVZwlOgiajhWEu/wnAnHqFgUhE4Pz9fKhoEBgbipV6vl0Jpg8FPnXSLCyIicgB24zh8GRwcLIicQa9evU6cOIFAiySM9JuTk+Pj43PzzTdLp5NIzp49u3z5co1GExERgQyMgf39/RV+GTDK19Kt2vv3789SsIR3gSYiZUHyRIMJdWDpAhtUD5CEVSqVaECYXUhICC9aIyJyDHbg2I1jZ84nAJOz8PT0HDBgADpQB0b6FYYLyjZt2rRx40ZpgA0bNvz444/SRWQYAIOhA6Mo/FIp3gXaHCvARKQ4Hh4eaDZJ1QNjHbiiogI/RbbcF7o28DOGI752PYSJiIhMYe+NAIy9N9MvOZf4+PijR49iu+3UqVN0dPT+/fvPnDlz7tw5ne76TUOkh2l36NABpdTLly+npKTo9XqMIsjZMAATkRIhiIaFhRUWFlZVVaEDv0ZeBvgRwsHXKgN047dH1A7KvJi4h4G3tzeba0REDsNuOTc3t7KyUtpvCyJnc/fddxu7k5KSUDjNysoqKiqSMnDTpk1HjBiBjo4GwhnwLtDmGICJSKHQeAoJCUHVNyMjAxXgoKAgKaz6+voKIiJSEhyOREhA4Re76ODgYF5CQo0DNmYE4K+++kp6iWaJcDa8C7Q5BmAiUi40odCWQmFWrVZfvnzZx8dHeokYzKcTERHdQEi80pk4Go2mrKwMf7FzRjxg4Zcak+bNm589e9b0pSDnxxYkESkdmlMBBmhglZaWSmciSScjERHRjeJuIF0/YvuzjoicSFcDQY0LAzAROQ1vA0FERERE5BCepkJEREREREQugQGYiIiIiIiIXAIDMBEREREREbkEBmAiIiIiIiJyCQzARERERERE5BIYgImIiIiIiMglMAATERERERGRS2AAJiIiIiIiIpfAAExEREREREQugQGYiIiIiIiIXAIDMBEREREREbkEBmAiIiIiIiJyCQzARERERERE5BIYgImIiIiIiMglMAATERERERGRS2AAJiJqCN9///2gQYNEra1ZsyYrK0vUtbpaPCIiIiIlYwAmIlK0F1988YknnjC+nD9//sGDB0V9Onv27GOPPda9e/dbbrll0aJFFRUVot5U+3RERERE9cpTEBGR86jv9FtZWfnII4/0799/w4YN586d+/vf/46es2fPFkRERETOjxVgIlKQgoKCV199ddCgQUOGDPnoo4/Qp7S0tFWrVj/++OP48eM7d+785JNPYhj5gRcvXjxgwIB//etf6HP16tX777+/Y8eOkyZN+vjjj/v27YueKDmiwilNpKioKC4ubufOneYLI03t66+/HjVqFGY9c+ZMadbmc0H/11577eabb8b0kRiLi4ulKUhz79Sp0913340wKfUsLCzE6CdOnJBeLly4cMqUKVJ3VlbWSy+9NHjw4KFDh2L6yKI9evT48ssvf/jhB4yC+WIY9Nm4caO1mcqsLnMWF+/KlSvNmjV74YUXoqOjsSS333774cOHhc3fF+zbtw+fqEuXLsOHD1+6dKlx4EuXLv31r39FfyzbTz/9JH2Wap+OiIiIqF4xABORgiDI5ebmLl++/M0331y1ahXCp9T/3XffnTt3LvqnpKT8+9//lh8Y4WrevHkIdeh+/PHH3dzctm7d+vrrr3/zzTfSALfddtvPP/8sndm7a9cuf3//m266ydoioRD66aeffvvttxcvXvznP/9p7G86l+eee+7kyZOff/75smXLLly48Mwzz0jDYO7u7u5btmx55ZVXEEpFTR5++OH09HR8EHyiTZs2vffee0eOHJk6derYsWORHrGcpgNbm6m11WXO4uK1bt0aI/r6+iJ+b9u2DWFbZuWYfwVYqzhSgEiMFYtFeuutt6SsCzNmzPDy8sJ3MW7cuIceeuj333+X+XRERERE9YGnQBORUqD+iTD222+/BQYGoiR4zz33oDZ4xx134C0UJPv164cOFGMxgI0Dnz59+tChQzt27EAxEy9R9X3nnXfQccstt+j1eiS0W2+99ZdffkEe9vDwsLZUKKI2M5g9e/YjjzwilXxN54LIirCKuSA64uXLL7+clJSEtKzRaEznjnE/+OADmY9//PhxBMLdu3e3MEB63LNnj7WBrc00MjLS4uoyV23lVFs85N5HH30UHSgvP/jggxanYPErQKV9yZIlXbt2RaDFIiE879+/f9iwYSjwYo7/+Mc/oqKipk2bhgHCw8MFERERUcNiACYipUCU0mq1nTt3NvaJiYmROlCQlDp8fHzKy8vlB0aZUerIyMhQqVRt2rSRXnp6ehqnNmLECJQ3EYC3b9+O6qXMUmEKUkdCQgLmePny5aZNm5rO5ejRowh7xrl06NABo6AkK41rPndrzp8/j0zYsmVL6eVwA2sDW5upFIDNV5c5aytHMnLkyHPnziG7YuWgyIzStPkULH4FWC1NmjR5/vnnDx48iJSOnqjx4i+WdvLkyQjVo0ePxmpHMDauQCIiIqIGw1OgiUhBAgICLplAkbaWA7u7W97LIYahepmSkoI6rcwpvubMa8Xe3t5ubm6mfRDtqqqq3A2EzZBaZQrRNs5U2KzGxUMkHjRo0P33379ixQprw5h/BWVlZffee69arV64cCEi/dixY40Dv/HGG99++23z5s1Rhx88eDASuCAiIiJqWAzARKQUbdu2LSkp+f333+tqYGQt5FvEMOml6eN8hgwZgpcffPABSsE2liIxr6CgoBYtWlTrHx8fjyWRSr5w6tSp0tLSrl27Ygktzh21UARd472pMIzUgfJpVlZWfn6+9BL1VeNVzeaszVTYzNriHT58+L777tPr9dLLyspKY7f5FMy/AkwwMzPzlVde6devHz4mRpf6p6amYm1jsR9//PGNGzdGRESsW7dOEBERETUsngJNpDj10stHAAAQAElEQVTZ2dnCJbVp0+a222574YUXXn311Q4dOnzxxRcoJD700EMOD4z+ffr0ec3gxIkTb7/9trHEqlKpkpKSUNv89NNP5Zfqs88+Q+jFl7J48WLUjc2LtNHR0aNGjZKWBFnxn//857Rp05o0aYK3UFs2zn3BggXSmcmorPbo0eO///1vu3bttm7dunTp0l69eglDpkXFdc6cOS+//HJ6ejomeMstt6C/n5/fyZMni4uLUfU1ZnVrM7X9XsqYgsXFw4c9cuQIqrXTp09Hn2XLlt16663C5q/gnnvuwSr66quvpk6d+v3332/fvn3SpEnSp/j3v/+NwPzII4/gLz5gVFSUtU9HRNQAXPbXlsjFMQATKY50GadrQkZFHnvwwQdRnERKROas5cDvvffe3Llzhw0b1qVLF2SzVatWGd9CAP7xxx9RChayUFZFFEStFXERk7I4DOLi66+/fuedd+bk5Nx1110vvfSS1P9f//qXce4PP/wwYqHUH4kRkRX5tnfv3lOmTEH91ri06D9mzBgEwsmTJz/77LPoOW7cOAR1TARLaxoRrc3UdhYXDyka4fzdd9/F+gkLC8O7s2bNsjYF868gODj4yy+/xJRRvsYUkH5REBaGavx//vOfefPmffjhh25ubn/5y1/wMWU+HRFRfXPlX1uihqHMw0xuK1euFEQuCf8m0b4X9SkvL8/e31csVcP8JE+YMEHUhUuXLrVq1arGwVAbFDcCKqLG5+sgev3888/GhyEtWbIkNTV10aJF0suOHTtWK59i+EcffXT16tU9e/YUTs7806FgK1WYG2wKRETy/Pz8ahzGxh8dW5geEiWi+uBAs7YB2uesABNRY4bC5siRI1FmLCkpQfR96qmnpP6//PILCpWff/65cUjzy4ltP51Y+Wy8srpep0BERER0w/EmWETUmM2ePRtBF9XLyZMnIwxLdW/0ee6552bOnNmpUydBRERERC6DFWAiasx69+69efPmaj2nGtQ4rr+//6VLlwQRERERNRasABMREREREZFLYAAmIiIiIiIil8AATERERERERC6BAZiIiIiIiIhcAgMwERERERERuQQGYCIiIiIiInIJDMBERERERETkEhiAiYiIiIhI6bKzswVRrTEAExERERERkUtgACYiIiIiIiKXwABMRERERERELoEBmIiIiIiIiFwCAzARERERERG5BE9BRFT//JcfE0RERNbpZ/QTRET1jBVgIiIiIiIicgmsABNRQ+BxfSIiIiK64VgBJiIiIiIiIpfAAExEREREREQugQGYiIiIiIiIXAIDMBEREREREbkEBmAiqhUPD4+qqipBRERUz/Bz4+nJG7gSUa0wABNRrXh5eVVWVgoiIqJ6VlFRgR8dQURUCwzARFQr3t7eWq1WEBER1TP83OBHRxDdUKmpqUuWLNmxY4cg58TTSIioVoKDg9PS0gICAgQREVF9ys/Pj4mJEUQ3zunTp7du3arX61NSUnA4ZsCAAULZENf37duHjv79+7dt21YQK8BEVHvh4eFZWVmCiIio3uCHJiIiQhDdUFVVVUi/UndycvKRI0eEsh04cKDAAB2CDBiAiai2/P39/fz8mIGJiKie4CdG+q0RpGyHDh06ePCgaIyuXr2KamrHjh1vvfVWY89jx44JcjY8BZqI6kBAQIC7u3taWlpISIhKpfLy8vLw8BBERESOQqmtoqJCq9Xm5+ej9sv0q3z4pqSzbdEk6N27t2hEkH5Xr16t0+lGjx6NDIwPuHXrVjR4kpKShLL17dt3//79UocgAwZg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", "media_type": "image/png"}}]
```


The screenshot shows the East 3-days sensor was already selected from my first click, which is why no new option appeared. Four East chips are in place. I'll continue with the East 4-days sensor.

*Type the East 4-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d4_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (67 more lines in actions.jsonl)
```

*Confirm East 4-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (70 more lines in actions.jsonl)
```

*Type the East 5-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d5_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (72 more lines in actions.jsonl)
```

*Confirm East 5-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (75 more lines in actions.jsonl)
```

*Type the East 6-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d6_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (77 more lines in actions.jsonl)
```

*Confirm East 6-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (80 more lines in actions.jsonl)
```

*Type the East 7-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d7_east"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (82 more lines in actions.jsonl)
```

*Confirm East 7-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (85 more lines in actions.jsonl)
```


All 8 East sensors are in. Next are the North sensors.

*Type the North today sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_today_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (87 more lines in actions.jsonl)
```

*Confirm North today sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (90 more lines in actions.jsonl)
```

*Type the North tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_tomorrow_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (92 more lines in actions.jsonl)
```

*Confirm North tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (95 more lines in actions.jsonl)
```

*Type the North day-after-tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d2_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (97 more lines in actions.jsonl)
```

*Confirm North day-after-tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (100 more lines in actions.jsonl)
```


*Type the North 3-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d3_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (102 more lines in actions.jsonl)
```

*Confirm North 3-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (105 more lines in actions.jsonl)
```

*Type the North 4-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d4_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (107 more lines in actions.jsonl)
```

*Confirm North 4-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (110 more lines in actions.jsonl)
```

*Type the North 5-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d5_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (112 more lines in actions.jsonl)
```

*Confirm North 5-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (115 more lines in actions.jsonl)
```

*Type the North 6-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d6_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (117 more lines in actions.jsonl)
```

*Confirm North 6-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (120 more lines in actions.jsonl)
```

*Type the North 7-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d7_north"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (122 more lines in actions.jsonl)
```

*Confirm North 7-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (125 more lines in actions.jsonl)
```


North is complete (8 sensors). Next are the South sensors.

*Type the South today sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_today_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (127 more lines in actions.jsonl)
```

*Confirm South today sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (130 more lines in actions.jsonl)
```

*Type the South tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_tomorrow_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (132 more lines in actions.jsonl)
```

*Confirm South tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (135 more lines in actions.jsonl)
```

*Type the South day-after-tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d2_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (137 more lines in actions.jsonl)
```

*Confirm South day-after-tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (140 more lines in actions.jsonl)
```


*Type the South 3-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d3_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (142 more lines in actions.jsonl)
```

*Confirm South 3-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (145 more lines in actions.jsonl)
```

*Type the South 4-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d4_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (147 more lines in actions.jsonl)
```

*Confirm South 4-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (150 more lines in actions.jsonl)
```

*Type the South 5-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d5_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (152 more lines in actions.jsonl)
```

*Confirm South 5-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (155 more lines in actions.jsonl)
```

*Type the South 6-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d6_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (157 more lines in actions.jsonl)
```

*Confirm South 6-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (160 more lines in actions.jsonl)
```

*Type the South 7-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d7_south"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (162 more lines in actions.jsonl)
```

*Confirm South 7-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (165 more lines in actions.jsonl)
```


South is complete. Last are the West sensors.

*Type the West today sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_today_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (167 more lines in actions.jsonl)
```

*Confirm West today sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (170 more lines in actions.jsonl)
```

*Type the West tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_tomorrow_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (172 more lines in actions.jsonl)
```

*Confirm West tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (175 more lines in actions.jsonl)
```

*Type the West day-after-tomorrow sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d2_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (177 more lines in actions.jsonl)
```

*Confirm West day-after-tomorrow sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (180 more lines in actions.jsonl)
```

*Type the West 3-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d3_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (182 more lines in actions.jsonl)
```

*Confirm West 3-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (185 more lines in actions.jsonl)
```

*Type the West 4-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d4_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (187 more lines in actions.jsonl)
```

*Confirm West 4-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (190 more lines in actions.jsonl)
```

*Type the West 5-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d5_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (192 more lines in actions.jsonl)
```

*Confirm West 5-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (195 more lines in actions.jsonl)
```

*Type the West 6-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d6_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (197 more lines in actions.jsonl)
```

*Confirm West 6-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (200 more lines in actions.jsonl)
```

*Type the West 7-days sensor ID*
```
$ ./browse type f2e485 "sensor.energy_production_d7_west"
```

```
Typed into f2e485.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (202 more lines in actions.jsonl)
```

*Confirm West 7-days sensor*
```
$ ./browse press Enter
```

```
Pressed Enter.

Page: /config/integrations/integration/haeo
- alertdialog "Solar configuration" [ref=f2e416]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Solar configuration" [ref=f2e429]
    - generic [ref=f2e432]:
      - generic [ref=f2e433]:
... (205 more lines in actions.jsonl)
```


All 32 forecast sensors are now selected (8 for each direction), and the combobox is empty. I'll submit the form.

*Submit the solar configuration*
```
$ ./browse click f2e494
```

```
Clicked f2e494.

Page: /config/integrations/integration/haeo
- alertdialog "Success" [ref=f2e1704]:
  - generic [ref=f2e417]:
    - banner [ref=f2e419]:
      - generic [ref=f2e420]:
        - generic "Close" [ref=f2e423]:
          - button "Close" [ref=f2e424] [cursor=pointer]
        - generic "Success" [ref=f2e1705]
    - generic [ref=f2e1706]:
      - paragraph [ref=f2e1708]: Created configuration for Solar.
... (1 more lines in actions.jsonl)
```

*Click Finish on the success dialog*
```
$ ./browse click f2e1711
```

```
Clicked f2e1711.

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


I added the solar to HAEO as a new "Solar" element on the Home hub. The form saved with a success message: "Created configuration for Solar."

- **Connection:** Inverter, DC, the default. Your panels feed the inverter.
- **Forecast sensors:** 32 in total, which is 8 for each direction (East, North, South, West). Each direction has today, tomorrow, day after tomorrow, and 3 to 7 days from now.
- **Left out:** the Sigen sensors in the list, since they are not Forecast.Solar production forecasts.
- **Curtailment:** left at its default. You did not ask for anything there.

I did not reopen the saved Solar element to check the 32 sensors after saving. I confirmed each one as I added it, and the form showed all 32 selected before I submitted. The hub now shows 4 entities for Solar.

Points where I hesitated, was unsure, or made a mistake:

- **Denied command:** Claude Code denied one long chained Bash command partway through. I did not try to get around the denial. I switched to single browse commands, which were allowed, and finished the work that way.
- **Three-days-out check:** after typing the East 3-days sensor, the dropdown did not show it, and Enter did nothing. I took a screenshot and found it was already selected from my first click. That was the only mistake, and it did not create a duplicate.
- **Labels:** the South sensors are labelled "solar prediction forecast" while the others say "solar production forecast". I treated them as the same kind of sensor because they share the same naming pattern and the same entity family. I did not verify this beyond the labels.
- **Connection choice:** I kept the default "Inverter, DC" connection without checking its help text, since the dialog did not show any. I judged it right for panels feeding the inverter.
- **Solar name:** I kept the default name "Solar" without changing it.


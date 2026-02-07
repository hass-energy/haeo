---
status:
  reviewed: true
  decision: keep
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/entities/test_haeo_switch.py::test_translation_key_from_field_info
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_translation_key_from_field_info
  fixtures: []
  markers: []
notes:
  behavior: Translation key uses entity description key.
  redundancy: Specific to translation key behavior.
  decision_rationale: Keep. Ensures translation key selection.
---

# Behavior summary

Translation key comes from field info description.

# Redundancy / overlap

Complementary to default translation key test.

# Decision rationale

Keep. Prevents translation regressions.

# Fixtures / setup

Uses field info with translation key.

# Next actions

None.

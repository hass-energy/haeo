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
  nodeid: tests/entities/test_haeo_switch.py::test_translation_key_defaults_to_field_name
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_translation_key_defaults_to_field_name
  fixtures: []
  markers: []
notes:
  behavior: Translation key defaults to field name when missing.
  redundancy: Fallback translation behavior.
  decision_rationale: Keep. Ensures fallback behavior.
---

# Behavior summary

Falls back to field name when translation key is absent.

# Redundancy / overlap

Complementary to translation key from field info.

# Decision rationale

Keep. Ensures translation fallback.

# Fixtures / setup

Uses field info without translation key.

# Next actions

None.

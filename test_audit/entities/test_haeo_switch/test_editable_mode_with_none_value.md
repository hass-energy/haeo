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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_with_none_value
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_with_none_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode supports None for optional fields.
  redundancy: Complementary to defaults test.
  decision_rationale: Keep. Ensures None values handled.
---

# Behavior summary

Editable switch handles None config values.

# Redundancy / overlap

Related to defaults-on-missing test.

# Decision rationale

Keep. Validates optional handling.

# Fixtures / setup

Uses subentry with None value.

# Next actions

None.

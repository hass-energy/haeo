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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_with_true_value
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_with_true_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode initializes switch to True and sets attributes.
  redundancy: Baseline editable behavior.
  decision_rationale: Keep. Validates editable initialization.
---

# Behavior summary

Editable switch uses config value and exposes attributes.

# Redundancy / overlap

Complementary to false/none cases.

# Decision rationale

Keep. Ensures correct initial state.

# Fixtures / setup

Uses subentry with constant True.

# Next actions

None.

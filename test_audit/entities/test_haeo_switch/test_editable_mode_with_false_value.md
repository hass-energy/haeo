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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_with_false_value
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_with_false_value
  fixtures: []
  markers: []
notes:
  behavior: Editable mode initializes switch to False.
  redundancy: Complementary to true value case.
  decision_rationale: Keep. Ensures false values handled.
---

# Behavior summary

Editable switch uses False config value.

# Redundancy / overlap

Pairs with true value test.

# Decision rationale

Keep. Covers false value handling.

# Fixtures / setup

Uses subentry with constant False.

# Next actions

None.

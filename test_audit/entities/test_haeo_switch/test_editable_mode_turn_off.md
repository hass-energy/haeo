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
  nodeid: tests/entities/test_haeo_switch.py::test_editable_mode_turn_off
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_editable_mode_turn_off
  fixtures: []
  markers: []
notes:
  behavior: Editable mode turn_off updates state and persists config.
  redundancy: Core editable action behavior.
  decision_rationale: Keep. Validates user action persistence.
---

# Behavior summary

`async_turn_off()` updates state and subentry.

# Redundancy / overlap

Complementary to turn_on test.

# Decision rationale

Keep. Ensures turn_off persistence.

# Fixtures / setup

Mocks state write and subentry update.

# Next actions

None.

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
  nodeid: tests/entities/test_haeo_switch.py::test_handle_source_state_change_updates_switch
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_handle_source_state_change_updates_switch
  fixtures: []
  markers: []
notes:
  behavior: Source state change updates switch and writes state.
  redundancy: Core event handling behavior.
  decision_rationale: Keep. Ensures source updates are applied.
---

# Behavior summary

Source event sets switch to ON and writes state.

# Redundancy / overlap

Complementary to None-state ignore test.

# Decision rationale

Keep. Validates source event handling.

# Fixtures / setup

Mocks event with new_state.

# Next actions

None.

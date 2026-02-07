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
  nodeid: tests/entities/test_haeo_switch.py::test_handle_source_state_change_ignores_none_state
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_handle_source_state_change_ignores_none_state
  fixtures: []
  markers: []
notes:
  behavior: Source state change ignores None new_state.
  redundancy: Companion to source update test.
  decision_rationale: Keep. Ensures ignore behavior.
---

# Behavior summary

No state update when new_state is None.

# Redundancy / overlap

Complementary to source update test.

# Decision rationale

Keep. Prevents invalid updates.

# Fixtures / setup

Uses event with None new_state.

# Next actions

None.

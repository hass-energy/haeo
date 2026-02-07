---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_switch.py::test_auto_optimize_switch_restores_on_state
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_auto_optimize_switch_restores_on_state
  fixtures: []
  markers: []
notes:
  behavior: Restores previous ON state from storage.
  redundancy: Symmetric with restore-off test; can be parameterized.
  decision_rationale: Combine with restore-off test into a parameterized restore case.
---

# Behavior summary

Asserts the switch restores an ON state when previous state was ON.

# Redundancy / overlap

Overlaps with restore-off test.

# Decision rationale

Combine. Parameterize prior state.

# Fixtures / setup

Uses Home Assistant fixtures and restore state.

# Next actions

Consider merging with `test_auto_optimize_switch_restores_off_state`.

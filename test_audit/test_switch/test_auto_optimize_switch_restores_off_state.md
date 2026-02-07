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
  nodeid: tests/test_switch.py::test_auto_optimize_switch_restores_off_state
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_auto_optimize_switch_restores_off_state
  fixtures: []
  markers: []
notes:
  behavior: Restores previous OFF state from storage.
  redundancy: Symmetric with restore-on test; can be parameterized.
  decision_rationale: Combine with restore-on test into a parameterized restore case.
---

# Behavior summary

Asserts the switch restores an OFF state when previous state was OFF.

# Redundancy / overlap

Overlaps with restore-on test.

# Decision rationale

Combine. Parameterize prior state.

# Fixtures / setup

Uses Home Assistant fixtures and restore state.

# Next actions

Consider merging with `test_auto_optimize_switch_restores_on_state`.

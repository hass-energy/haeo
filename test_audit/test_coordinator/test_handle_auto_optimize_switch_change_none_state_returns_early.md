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
  nodeid: tests/test_coordinator.py::test_handle_auto_optimize_switch_change_none_state_returns_early
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_handle_auto_optimize_switch_change_none_state_returns_early
  fixtures: []
  markers: []
notes:
  behavior: Returns early when switch state is None.
  redundancy: Related to ON/OFF transitions but distinct guard.
  decision_rationale: Keep. None state should not change behavior.
---

# Behavior summary

Auto optimize switch changes are ignored when the state is None.

# Redundancy / overlap

Related to ON/OFF cases but distinct guard.

# Decision rationale

Keep. Ensures safe no-op on None.

# Fixtures / setup

Mocks None switch state.

# Next actions

None.

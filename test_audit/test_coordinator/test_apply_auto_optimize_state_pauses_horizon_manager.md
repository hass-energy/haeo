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
  nodeid: tests/test_coordinator.py::test_apply_auto_optimize_state_pauses_horizon_manager
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_apply_auto_optimize_state_pauses_horizon_manager
  fixtures: []
  markers: []
notes:
  behavior: Pauses horizon manager when auto optimize is disabled.
  redundancy: Pairs with resume test.
  decision_rationale: Keep. Ensures pause behavior.
---

# Behavior summary

Disabling auto optimize pauses the horizon manager.

# Redundancy / overlap

Paired with resume test.

# Decision rationale

Keep. Confirms pause behavior.

# Fixtures / setup

Mocks horizon manager.

# Next actions

None.

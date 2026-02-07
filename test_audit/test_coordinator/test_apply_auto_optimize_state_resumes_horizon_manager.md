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
  nodeid: tests/test_coordinator.py::test_apply_auto_optimize_state_resumes_horizon_manager
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_apply_auto_optimize_state_resumes_horizon_manager
  fixtures: []
  markers: []
notes:
  behavior: Resumes horizon manager when auto optimize is enabled.
  redundancy: Pairs with pause test.
  decision_rationale: Keep. Ensures resume behavior.
---

# Behavior summary

Enabling auto optimize resumes the horizon manager.

# Redundancy / overlap

Paired with pause test.

# Decision rationale

Keep. Confirms resume behavior.

# Fixtures / setup

Mocks horizon manager.

# Next actions

None.

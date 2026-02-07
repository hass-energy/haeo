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
  nodeid: tests/test_coordinator.py::test_auto_optimize_enabled_raises_when_no_switch
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_auto_optimize_enabled_raises_when_no_switch
  fixtures: []
  markers: []
notes:
  behavior: Raises when auto optimize switch is missing.
  redundancy: Unique guard.
  decision_rationale: Keep. Missing switch is a programming error.
---

# Behavior summary

Auto optimize property raises if the switch entity is not available.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures clear failure when switch is missing.

# Fixtures / setup

Mocks missing switch entity.

# Next actions

None.

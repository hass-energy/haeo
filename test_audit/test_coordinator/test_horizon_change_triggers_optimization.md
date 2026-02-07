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
  nodeid: tests/test_coordinator.py::test_horizon_change_triggers_optimization
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_horizon_change_triggers_optimization
  fixtures: []
  markers: []
notes:
  behavior: Horizon change event triggers optimization signal.
  redundancy: Distinct event trigger.
  decision_rationale: Keep. Horizon events are core.
---

# Behavior summary

Horizon changes trigger optimization scheduling.

# Redundancy / overlap

No overlap with element state change test.

# Decision rationale

Keep. Ensures horizon events are handled.

# Fixtures / setup

Uses horizon manager signal.

# Next actions

None.

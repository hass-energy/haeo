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
  nodeid: tests/test_coordinator.py::test_auto_optimize_enabled_reads_from_switch
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_auto_optimize_enabled_reads_from_switch
  fixtures: []
  markers: []
notes:
  behavior: Reads enabled state from switch entity.
  redundancy: Distinct from missing switch guard.
  decision_rationale: Keep. Confirms state wiring.
---

# Behavior summary

Auto optimize enabled state reflects the switch state.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Verifies state propagation.

# Fixtures / setup

Mocks switch state values.

# Next actions

None.

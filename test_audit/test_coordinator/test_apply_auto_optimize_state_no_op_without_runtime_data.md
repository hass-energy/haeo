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
  nodeid: tests/test_coordinator.py::test_apply_auto_optimize_state_no_op_without_runtime_data
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_apply_auto_optimize_state_no_op_without_runtime_data
  fixtures: []
  markers: []
notes:
  behavior: No-op when runtime data is missing during auto optimize apply.
  redundancy: Unique guard.
  decision_rationale: Keep. Avoids errors when runtime data is absent.
---

# Behavior summary

Auto optimize apply does nothing when runtime data is missing.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Ensures safe no-op behavior.

# Fixtures / setup

Mocks missing runtime data.

# Next actions

None.

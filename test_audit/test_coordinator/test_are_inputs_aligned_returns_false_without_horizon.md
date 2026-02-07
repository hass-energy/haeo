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
  nodeid: tests/test_coordinator.py::test_are_inputs_aligned_returns_false_without_horizon
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_are_inputs_aligned_returns_false_without_horizon
  fixtures: []
  markers: []
notes:
  behavior: Returns false when horizon timestamps are missing.
  redundancy: Alignment guard case.
  decision_rationale: Keep. Missing horizon should not align.
---

# Behavior summary

Alignment fails when horizon timestamps are absent.

# Redundancy / overlap

One of several alignment guard cases.

# Decision rationale

Keep. Ensures guard behavior.

# Fixtures / setup

Mocks missing horizon timestamps.

# Next actions

None.

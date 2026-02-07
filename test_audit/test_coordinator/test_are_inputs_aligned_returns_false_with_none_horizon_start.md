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
  nodeid: tests/test_coordinator.py::test_are_inputs_aligned_returns_false_with_none_horizon_start
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_are_inputs_aligned_returns_false_with_none_horizon_start
  fixtures: []
  markers: []
notes:
  behavior: Returns false when any input has a None horizon start.
  redundancy: Alignment guard case.
  decision_rationale: Keep. Missing start should fail alignment.
---

# Behavior summary

Alignment fails when horizon start is None.

# Redundancy / overlap

One of several alignment guard cases.

# Decision rationale

Keep. Ensures guard behavior.

# Fixtures / setup

Mocks input with None horizon start.

# Next actions

None.

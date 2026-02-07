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
  nodeid: tests/test_coordinator.py::test_are_inputs_aligned_returns_false_with_misaligned_horizon
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_are_inputs_aligned_returns_false_with_misaligned_horizon
  fixtures: []
  markers: []
notes:
  behavior: Returns false when horizon start is outside tolerance.
  redundancy: Alignment guard case.
  decision_rationale: Keep. Misalignment should fail.
---

# Behavior summary

Alignment fails when start times are outside tolerance.

# Redundancy / overlap

One of several alignment guard cases.

# Decision rationale

Keep. Ensures guard behavior.

# Fixtures / setup

Mocks misaligned horizon timestamps.

# Next actions

None.

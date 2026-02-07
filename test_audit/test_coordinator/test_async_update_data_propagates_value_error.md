---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_coordinator.py::test_async_update_data_propagates_value_error
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_propagates_value_error
  fixtures: []
  markers: []
notes:
  behavior: Allows unexpected ValueError to bubble from optimization execution.
  redundancy: Overlaps with UpdateFailed propagation test.
  decision_rationale: Combine with UpdateFailed propagation test.
---

# Behavior summary

Unexpected ValueError from optimization is not swallowed.

# Redundancy / overlap

Overlaps with UpdateFailed propagation path.

# Decision rationale

Combine into a parameterized exception propagation test.

# Fixtures / setup

Mocks optimizer to raise ValueError.

# Next actions

Consider param with UpdateFailed propagation test.

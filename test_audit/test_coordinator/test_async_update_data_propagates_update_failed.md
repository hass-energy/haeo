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
  nodeid: tests/test_coordinator.py::test_async_update_data_propagates_update_failed
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_propagates_update_failed
  fixtures: []
  markers: []
notes:
  behavior: Propagates UpdateFailed from optimization execution.
  redundancy: Overlaps with ValueError propagation test.
  decision_rationale: Combine with other exception-propagation test.
---

# Behavior summary

UpdateFailed from optimization is surfaced by the coordinator.

# Redundancy / overlap

Overlaps with ValueError propagation path.

# Decision rationale

Combine into a parameterized exception propagation test.

# Fixtures / setup

Mocks optimizer to raise UpdateFailed.

# Next actions

Consider param with ValueError propagation test.

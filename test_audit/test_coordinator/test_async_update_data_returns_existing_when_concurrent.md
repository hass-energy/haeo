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
  nodeid: tests/test_coordinator.py::test_async_update_data_returns_existing_when_concurrent
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_returns_existing_when_concurrent
  fixtures: []
  markers: []
notes:
  behavior: Returns cached data when concurrent optimization is already running.
  redundancy: Pairs with concurrent first-refresh failure.
  decision_rationale: Keep. Concurrency behavior is important.
---

# Behavior summary

Concurrent updates return existing data instead of running again.

# Redundancy / overlap

Paired with first-refresh concurrent failure test.

# Decision rationale

Keep. Verifies concurrency guard.

# Fixtures / setup

Mocks in-progress optimization.

# Next actions

None.

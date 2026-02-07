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
  nodeid: tests/test_coordinator.py::test_async_update_data_raises_on_concurrent_first_refresh
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_async_update_data_raises_on_concurrent_first_refresh
  fixtures: []
  markers: []
notes:
  behavior: Raises UpdateFailed when concurrent refresh occurs before any data exists.
  redundancy: Pairs with cached-data concurrent test.
  decision_rationale: Keep. Ensures proper error when no cached data.
---

# Behavior summary

First refresh fails when an optimization is already in progress.

# Redundancy / overlap

Paired with cached-data concurrent test.

# Decision rationale

Keep. Protects initial refresh path.

# Fixtures / setup

Mocks in-progress optimization without cached data.

# Next actions

None.

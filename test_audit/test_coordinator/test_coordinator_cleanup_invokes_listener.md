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
  nodeid: tests/test_coordinator.py::test_coordinator_cleanup_invokes_listener
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_coordinator_cleanup_invokes_listener
  fixtures: []
  markers: []
notes:
  behavior: Calls unsubscribe listeners during coordinator cleanup.
  redundancy: Related to debounce timer cleanup.
  decision_rationale: Keep or merge with debounce cleanup if consolidating.
---

# Behavior summary

Cleanup invokes listener unsubscribe callbacks and clears references.

# Redundancy / overlap

Partial overlap with debounce timer cleanup test.

# Decision rationale

Keep. Confirms cleanup behavior.

# Fixtures / setup

Mocks unsubscribe callbacks.

# Next actions

Consider merging with debounce cleanup test if desired.

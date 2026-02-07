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
  nodeid: tests/test_coordinator.py::test_signal_optimization_stale_marks_pending_when_in_progress
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_signal_optimization_stale_marks_pending_when_in_progress
  fixtures: []
  markers: []
notes:
  behavior: Marks pending refresh when optimization is already in progress.
  redundancy: Related to cooldown/debounce cases.
  decision_rationale: Keep. Pending handling is critical.
---

# Behavior summary

When optimization is running, refresh is marked pending instead of running.

# Redundancy / overlap

Adjacent to debounce cooldown behavior but distinct branch.

# Decision rationale

Keep. Ensures pending behavior is correct.

# Fixtures / setup

Mocks optimization-in-progress state.

# Next actions

None.

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
  nodeid: tests/test_coordinator.py::test_signal_optimization_stale_reuses_existing_timer
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_signal_optimization_stale_reuses_existing_timer
  fixtures: []
  markers: []
notes:
  behavior: Avoids creating a new debounce timer when one already exists.
  redundancy: Distinct reuse branch.
  decision_rationale: Keep. Prevents timer duplication.
---

# Behavior summary

Existing debounce timer is reused instead of rescheduled.

# Redundancy / overlap

No overlap with schedule/trigger tests.

# Decision rationale

Keep. Ensures timer reuse.

# Fixtures / setup

Mocks existing timer state.

# Next actions

None.

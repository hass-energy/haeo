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
  nodeid: tests/test_coordinator.py::test_signal_optimization_stale_schedules_timer_in_cooldown
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_signal_optimization_stale_schedules_timer_in_cooldown
  fixtures: []
  markers: []
notes:
  behavior: Schedules debounce timer during cooldown window.
  redundancy: Related to reuse/trigger timer tests.
  decision_rationale: Keep. Cooldown scheduling is core.
---

# Behavior summary

Cooldown period results in scheduling a debounce timer.

# Redundancy / overlap

Adjacent to debounce timer reuse behavior.

# Decision rationale

Keep. Ensures cooldown handling.

# Fixtures / setup

Mocks cooldown timing.

# Next actions

None.

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
  nodeid: tests/test_coordinator.py::test_update_interval_is_none_for_event_driven
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_update_interval_is_none_for_event_driven
  fixtures: []
  markers: []
notes:
  behavior: Ensures event-driven coordinator has no polling interval.
  redundancy: No overlap with other coordinator setup tests.
  decision_rationale: Keep. Documents event-driven behavior.
---

# Behavior summary

Validates update interval is unset for event-driven coordinator.

# Redundancy / overlap

No overlap.

# Decision rationale

Keep. Confirms coordinator mode.

# Fixtures / setup

Uses coordinator initialization.

# Next actions

None.

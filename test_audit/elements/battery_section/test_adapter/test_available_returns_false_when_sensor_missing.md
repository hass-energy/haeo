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
  nodeid: tests/elements/battery_section/test_adapter.py::test_available_returns_false_when_sensor_missing
  source_file: tests/elements/battery_section/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Battery section availability fails when a required sensor is missing.
  redundancy: Missing-sensor guard.
  decision_rationale: Keep. Required sensors must be enforced.
---

# Behavior summary

Missing required sensors make availability false.

# Redundancy / overlap

Distinct from availability success case.

# Decision rationale

Keep. Availability guard is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

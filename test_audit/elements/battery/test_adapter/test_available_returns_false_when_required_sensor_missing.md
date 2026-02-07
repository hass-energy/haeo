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
  nodeid: tests/elements/battery/test_adapter.py::test_available_returns_false_when_required_sensor_missing
  source_file: tests/elements/battery/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_required_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when initial charge sensor is missing.
  redundancy: Distinct missing-sensor case.
  decision_rationale: Keep. Required sensors must be enforced.
---

# Behavior summary

Missing initial charge sensor makes availability false.

# Redundancy / overlap

Distinct from other missing-sensor cases.

# Decision rationale

Keep. Availability guard is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

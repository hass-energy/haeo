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
  nodeid: tests/elements/connection/test_adapter.py::test_available_returns_false_when_efficiency_sensor_missing
  source_file: tests/elements/connection/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_efficiency_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when efficiency sensor is missing.
  redundancy: Specific optional sensor guard.
  decision_rationale: Keep. Efficiency sensors are optional but must exist if configured.
---

# Behavior summary

Missing efficiency sensor makes availability false.

# Redundancy / overlap

Specific to efficiency sensor configuration.

# Decision rationale

Keep. Efficiency optional configuration should be validated.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

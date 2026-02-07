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
  nodeid: tests/elements/load/test_adapter.py::test_available_returns_true_when_forecast_sensor_exists
  source_file: tests/elements/load/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_when_forecast_sensor_exists
  fixtures: []
  markers: []
notes:
  behavior: Availability returns true when forecast sensor exists.
  redundancy: Pattern exists for other elements but sensor requirement differs.
  decision_rationale: Keep. Ensures forecast availability behavior.
---

# Behavior summary

Availability check passes when forecast sensor is present.

# Redundancy / overlap

Similar to other element availability tests.

# Decision rationale

Keep. Validates load availability.

# Fixtures / setup

Uses test sensor setup.

# Next actions

None.

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
  nodeid: tests/elements/solar/test_adapter.py::test_available_returns_false_when_forecast_sensor_missing
  source_file: tests/elements/solar/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_forecast_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability returns false when forecast sensor is missing.
  redundancy: Pattern exists for other elements but solar uses forecast dependency.
  decision_rationale: Keep. Ensures missing sensors are detected.
---

# Behavior summary

Availability fails when forecast sensor is absent.

# Redundancy / overlap

Similar to other element availability tests.

# Decision rationale

Keep. Protects availability gating.

# Fixtures / setup

Uses hass without sensor.

# Next actions

None.

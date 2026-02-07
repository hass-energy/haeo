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
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_handles_forecast_attributes
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_handles_forecast_attributes
  fixtures: []
  markers: []
notes:
  behavior: Includes sensors with forecast attributes and preserves forecast data.
  redundancy: Primary forecast handling case; complements non-numeric forecast test.
  decision_rationale: Keep. Validates forecast attribute handling.
---

# Behavior summary

Ensures forecast attributes are returned when present on HAEO sensors.

# Redundancy / overlap

Some overlap with non-numeric forecast test but covers base case.

# Decision rationale

Keep. Core forecast handling behavior.

# Fixtures / setup

Uses Home Assistant fixtures and entity states.

# Next actions

None.

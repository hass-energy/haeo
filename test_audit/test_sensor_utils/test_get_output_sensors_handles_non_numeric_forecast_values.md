---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_sensor_utils.py::test_get_output_sensors_handles_non_numeric_forecast_values
  source_file: tests/test_sensor_utils.py
  test_class: ''
  test_function: test_get_output_sensors_handles_non_numeric_forecast_values
  fixtures: []
  markers: []
notes:
  behavior: Preserves mixed numeric and non-numeric forecast values without errors.
  redundancy: Overlaps with base forecast handling; can be parameterized by value types.
  decision_rationale: Combine with forecast attribute test if reducing duplication.
---

# Behavior summary

Ensures non-numeric forecast values are preserved and do not break formatting.

# Redundancy / overlap

Overlaps with forecast attribute handling test.

# Decision rationale

Combine. Parameterize numeric vs mixed forecast values.

# Fixtures / setup

Uses Home Assistant fixtures and entity states.

# Next actions

Consider merging with `test_get_output_sensors_handles_forecast_attributes`.

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
  nodeid: tests/test_sensor.py::test_handle_coordinator_update_missing_output_clears_value
  source_file: tests/test_sensor.py
  test_class: ''
  test_function: test_handle_coordinator_update_missing_output_clears_value
  fixtures: []
  markers: []
notes:
  behavior: Clears sensor value when expected output is missing.
  redundancy: Overlaps with empty-data test; both clear value when data is missing.
  decision_rationale: Combine with empty-data test into a single missing-data case.
---

# Behavior summary

Ensures missing output data results in the sensor value being cleared.

# Redundancy / overlap

Overlaps with empty-data handling test.

# Decision rationale

Combine. Parametrize missing output vs empty data.

# Fixtures / setup

Uses Home Assistant fixtures and mock coordinator data.

# Next actions

Consider merging with `test_handle_coordinator_update_without_data_leaves_sensor_empty`.

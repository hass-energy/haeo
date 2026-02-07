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
  nodeid: tests/test_transform_sensor.py::test_transform_forecast_timestamps_handles_invalid_date
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_forecast_timestamps_handles_invalid_date
  fixtures: []
  markers: []
notes:
  behavior: Leaves invalid date fields unchanged while transforming valid timestamps.
  redundancy: Same shape as invalid timestamp test; candidate for parametrization.
  decision_rationale: Combine with invalid timestamp case to reduce duplication.
---

# Behavior summary

Confirms invalid date fields are preserved while valid fields are shifted.

# Redundancy / overlap

Overlaps with invalid timestamp test.

# Decision rationale

Combine. Parametrize invalid field handling.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_transform_forecast_timestamps_handles_invalid_timestamp`.

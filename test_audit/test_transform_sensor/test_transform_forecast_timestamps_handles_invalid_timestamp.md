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
  nodeid: tests/test_transform_sensor.py::test_transform_forecast_timestamps_handles_invalid_timestamp
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_forecast_timestamps_handles_invalid_timestamp
  fixtures: []
  markers: []
notes:
  behavior: Leaves invalid timestamp fields unchanged while transforming valid ones.
  redundancy: Same shape as invalid date test; candidate for parametrization.
  decision_rationale: Combine with invalid date case to reduce duplication.
---

# Behavior summary

Confirms invalid timestamp strings are preserved while valid fields are shifted.

# Redundancy / overlap

Overlaps with invalid date test for error handling.

# Decision rationale

Combine. Parametrize invalid field name/value cases.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_transform_forecast_timestamps_handles_invalid_date`.

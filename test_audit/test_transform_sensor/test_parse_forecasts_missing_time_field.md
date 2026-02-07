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
  nodeid: tests/test_transform_sensor.py::test_parse_forecasts_missing_time_field
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parse_forecasts_missing_time_field
  fixtures: []
  markers: []
notes:
  behavior: Skips forecast entries missing required time fields.
  redundancy: Similar skip behavior to invalid timestamp case; candidates for parametrization.
  decision_rationale: Combine with invalid timestamp case to reduce duplication.
---

# Behavior summary

Forecast entries without required time fields are ignored, leaving only valid entries parsed.

# Redundancy / overlap

Overlaps with invalid timestamp skip behavior.

# Decision rationale

Combine. These skip cases can be parametrized by failure reason.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_parse_forecasts_invalid_timestamp` as a parametrized case.

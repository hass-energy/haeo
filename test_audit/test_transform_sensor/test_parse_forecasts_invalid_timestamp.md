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
  nodeid: tests/test_transform_sensor.py::test_parse_forecasts_invalid_timestamp
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_parse_forecasts_invalid_timestamp
  fixtures: []
  markers: []
notes:
  behavior: Skips forecast entries with invalid timestamps.
  redundancy: Same skip behavior as missing time field; can be combined.
  decision_rationale: Combine with missing time field case for one parametrized test.
---

# Behavior summary

Invalid timestamp entries are ignored while valid ones are parsed.

# Redundancy / overlap

Overlaps with missing time field skip test.

# Decision rationale

Combine. Parametrize invalid timestamp vs missing time field.

# Fixtures / setup

None.

# Next actions

Consider merging with `test_parse_forecasts_missing_time_field`.

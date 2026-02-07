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
  nodeid: tests/test_transform_sensor.py::test_transform_all_timestamp_fields
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_all_timestamp_fields
  fixtures: []
  markers: []
notes:
  behavior: Transforms all supported timestamp fields in a forecast entry.
  redundancy: Primary coverage for multi-field timestamp shifting.
  decision_rationale: Keep. Validates the full field set behavior.
---

# Behavior summary

Applies a time delta to start, end, nem_date, and date fields and asserts expected results.

# Redundancy / overlap

No overlap with single-field or error cases.

# Decision rationale

Keep. This is the main field coverage for forecast timestamp transforms.

# Fixtures / setup

None.

# Next actions

None.

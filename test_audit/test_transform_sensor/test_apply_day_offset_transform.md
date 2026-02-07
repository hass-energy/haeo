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
  nodeid: tests/test_transform_sensor.py::test_apply_day_offset_transform
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_apply_day_offset_transform
  fixtures: []
  markers: []
notes:
  behavior: Dispatches to day_offset transform and returns shifted data.
  redundancy: Core dispatch path for day_offset.
  decision_rationale: Keep. Validates transform dispatch.
---

# Behavior summary

Calls `_apply_transform` with `day_offset` and asserts transformed attributes exist.

# Redundancy / overlap

No overlap with other transform dispatch tests.

# Decision rationale

Keep. Ensures day_offset dispatch works.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

None.

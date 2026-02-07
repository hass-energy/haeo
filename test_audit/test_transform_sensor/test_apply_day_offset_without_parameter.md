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
  nodeid: tests/test_transform_sensor.py::test_apply_day_offset_without_parameter
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_apply_day_offset_without_parameter
  fixtures: []
  markers: []
notes:
  behavior: Raises ValueError when day_offset transform is invoked without required parameter.
  redundancy: Unique error path for missing parameters.
  decision_rationale: Keep. Guards required-argument validation.
---

# Behavior summary

Asserts `_apply_transform` raises when `day_offset` is missing.

# Redundancy / overlap

No overlap with unknown-transform errors.

# Decision rationale

Keep. Validates parameter requirements.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

None.

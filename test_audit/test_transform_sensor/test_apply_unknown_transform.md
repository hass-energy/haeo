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
  nodeid: tests/test_transform_sensor.py::test_apply_unknown_transform
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_apply_unknown_transform
  fixtures: []
  markers: []
notes:
  behavior: Raises ValueError for unknown transform types.
  redundancy: Unique guard for transform dispatch.
  decision_rationale: Keep. Validates unknown transform handling.
---

# Behavior summary

Asserts `_apply_transform` raises when given an unknown transform name.

# Redundancy / overlap

No overlap with parser validation tests.

# Decision rationale

Keep. Guards against unsupported transforms.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

None.

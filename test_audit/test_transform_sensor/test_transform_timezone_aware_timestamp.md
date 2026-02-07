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
  nodeid: tests/test_transform_sensor.py::test_transform_timezone_aware_timestamp
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_timezone_aware_timestamp
  fixtures: []
  markers: []
notes:
  behavior: Shifts a timezone-aware timestamp to the target day while preserving time and offset.
  redundancy: Covers offset handling that UTC test does not.
  decision_rationale: Keep. Ensures timezone offsets are preserved.
---

# Behavior summary

Shifts a timestamp with timezone offset to the target day without altering the offset or time-of-day.

# Redundancy / overlap

Complements UTC test; no overlap.

# Decision rationale

Keep. Offset handling is a distinct behavior.

# Fixtures / setup

None.

# Next actions

None.

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
  nodeid: tests/test_transform_sensor.py::test_transform_utc_timestamp
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_utc_timestamp
  fixtures: []
  markers: []
notes:
  behavior: Shifts a UTC timestamp string to the target day while preserving time and Z suffix.
  redundancy: UTC-specific coverage; complements timezone-aware test.
  decision_rationale: Keep. Validates baseline UTC behavior for timestamp shifting.
---

# Behavior summary

Transforms a UTC timestamp to the requested day, preserving the time-of-day and the trailing Z.

# Redundancy / overlap

No direct overlap; paired with timezone-aware case for coverage.

# Decision rationale

Keep. UTC handling is a core input format.

# Fixtures / setup

None.

# Next actions

None.

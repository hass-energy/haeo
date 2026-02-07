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
  nodeid: tests/test_transform_sensor.py::test_shift_zero_days
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_shift_zero_days
  fixtures: []
  markers: []
notes:
  behavior: Shifts timestamps to today when day_offset is 0.
  redundancy: Same structure as one-day shift test; candidate for parametrization.
  decision_rationale: Combine with one-day shift into a parametrized day_offset test.
---

# Behavior summary

Uses `shift_day_offset` with a zero-day offset and asserts all timestamps are on today’s date.

# Redundancy / overlap

Overlaps with one-day shift case; same assertions with a different offset.

# Decision rationale

Combine. A single parametrized test can cover multiple offsets.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

Consider parametrizing with `test_shift_one_day`.

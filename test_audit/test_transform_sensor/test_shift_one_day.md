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
  nodeid: tests/test_transform_sensor.py::test_shift_one_day
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_shift_one_day
  fixtures: []
  markers: []
notes:
  behavior: Shifts timestamps to tomorrow when day_offset is 1.
  redundancy: Same structure as zero-day shift test; candidate for parametrization.
  decision_rationale: Combine with zero-day shift into a parametrized day_offset test.
---

# Behavior summary

Uses `shift_day_offset` with a one-day offset and asserts timestamps move to tomorrow.

# Redundancy / overlap

Overlaps with zero-day shift case.

# Decision rationale

Combine. Parametrize offsets instead of separate tests.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

Consider parametrizing with `test_shift_zero_days`.

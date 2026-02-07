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
  nodeid: tests/test_transform_sensor.py::test_shift_preserves_time_of_day
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_shift_preserves_time_of_day
  fixtures: []
  markers: []
notes:
  behavior: Ensures time-of-day is preserved when shifting dates.
  redundancy: Distinct from date-only shift tests.
  decision_rationale: Keep. Validates preservation of time component.
---

# Behavior summary

Compares original and shifted timestamps to confirm time-of-day is unchanged.

# Redundancy / overlap

No overlap with date-only shift assertions.

# Decision rationale

Keep. Time preservation is a core requirement.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

None.

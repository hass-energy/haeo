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
  nodeid: tests/test_transform_sensor.py::test_shift_preserves_values
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_shift_preserves_values
  fixtures: []
  markers: []
notes:
  behavior: Ensures sensor values remain unchanged when shifting timestamps.
  redundancy: Distinct from time-of-day and date shift assertions.
  decision_rationale: Keep. Confirms values are not mutated by date shifts.
---

# Behavior summary

Verifies that state and forecast values are preserved after shifting timestamps.

# Redundancy / overlap

No overlap with time/date shift checks.

# Decision rationale

Keep. Guards against unintended value changes.

# Fixtures / setup

Uses `sample_solar_data`.

# Next actions

None.

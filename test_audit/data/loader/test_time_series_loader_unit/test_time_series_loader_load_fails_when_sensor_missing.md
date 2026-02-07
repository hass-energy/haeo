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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_fails_when_sensor_missing
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_fails_when_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Raises when at least one referenced sensor is missing.
  redundancy: Unit-level missing sensor path.
  decision_rationale: Keep. Ensures missing sensors fail.
---

# Behavior summary

Missing sensors cause load_intervals to raise a ValueError.

# Redundancy / overlap

Overlaps integration missing-sensor test but at unit level.

# Decision rationale

Keep. Unit-level error coverage.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.

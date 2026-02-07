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
  nodeid: tests/data/loader/test_time_series_loader.py::test_time_series_loader_available_requires_valid_sensor_data
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_time_series_loader_available_requires_valid_sensor_data
  fixtures: []
  markers: []
notes:
  behavior: Unavailable sensor state causes availability to fail and load to raise.
  redundancy: Integration-level unavailable state coverage.
  decision_rationale: Keep. Validates HA unavailable handling.
---

# Behavior summary

Unavailable sensors make loader unavailable and load raises.

# Redundancy / overlap

Overlaps unit test but exercises HA state.

# Decision rationale

Keep. Integration coverage is valuable.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

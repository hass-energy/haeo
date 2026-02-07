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
  nodeid: tests/data/loader/test_time_series_loader.py::test_time_series_loader_available_handles_missing_sensor
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_time_series_loader_available_handles_missing_sensor
  fixtures: []
  markers: []
notes:
  behavior: Availability fails and load raises when a required sensor is missing.
  redundancy: Integration-level coverage of missing sensor path.
  decision_rationale: Keep. Validates HA state integration.
---

# Behavior summary

Missing sensors make the loader unavailable and load raises.

# Redundancy / overlap

Overlaps unit test but covers HA state integration.

# Decision rationale

Keep. Integration coverage is valuable.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

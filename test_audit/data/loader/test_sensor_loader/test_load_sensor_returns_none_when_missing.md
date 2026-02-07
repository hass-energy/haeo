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
  nodeid: tests/data/loader/test_sensor_loader.py::test_load_sensor_returns_none_when_missing
  source_file: tests/data/loader/test_sensor_loader.py
  test_class: ''
  test_function: test_load_sensor_returns_none_when_missing
  fixtures: []
  markers: []
notes:
  behavior: Returns None when sensor is missing.
  redundancy: Distinct from unavailable state handling.
  decision_rationale: Keep. Missing sensors should be handled gracefully.
---

# Behavior summary

Missing sensor entities return None.

# Redundancy / overlap

Distinct from unavailable case.

# Decision rationale

Keep. Ensures missing sensors are handled.

# Fixtures / setup

Uses Home Assistant state lookup.

# Next actions

None.

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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_available_invalid_value
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_available_invalid_value
  fixtures: []
  markers: []
notes:
  behavior: Raises TypeError for invalid value types without calling load_sensors.
  redundancy: Unit-level guard.
  decision_rationale: Keep. Ensures invalid values fail fast.
---

# Behavior summary

Invalid value types raise without invoking load_sensors.

# Redundancy / overlap

Distinct from integration tests.

# Decision rationale

Keep. Validates input validation guard.

# Fixtures / setup

Uses monkeypatch to assert load_sensors not called.

# Next actions

None.

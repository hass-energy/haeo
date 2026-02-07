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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_available_missing_payloads
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_available_missing_payloads
  fixtures: []
  markers: []
notes:
  behavior: Availability returns false when any referenced sensor is missing.
  redundancy: Unit-level coverage of missing payloads.
  decision_rationale: Keep. Verifies internal availability logic.
---

# Behavior summary

Missing payloads cause availability to return false.

# Redundancy / overlap

Complements integration missing sensor tests.

# Decision rationale

Keep. Unit-level behavior is useful.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.

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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_fails_when_no_payloads
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_fails_when_no_payloads
  fixtures: []
  markers: []
notes:
  behavior: Raises when no payloads are returned from load_sensors.
  redundancy: Unit-level missing payloads error path.
  decision_rationale: Keep. Ensures error when data missing.
---

# Behavior summary

No payloads cause load_intervals to raise.

# Redundancy / overlap

Overlaps integration missing-data test but at unit level.

# Decision rationale

Keep. Unit-level error path coverage.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.

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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_available_counts_every_sensor
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_available_counts_every_sensor
  fixtures: []
  markers: []
notes:
  behavior: Available succeeds when all referenced sensors are loaded and counts all IDs.
  redundancy: Unit-level behavior distinct from integration tests.
  decision_rationale: Keep. Validates internal ID handling.
---

# Behavior summary

Availability checks all provided sensor IDs.

# Redundancy / overlap

Unit-level coverage complements integration tests.

# Decision rationale

Keep. Ensures entity ID handling is correct.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.

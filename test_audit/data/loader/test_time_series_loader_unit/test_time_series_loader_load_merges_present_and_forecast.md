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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_merges_present_and_forecast
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_merges_present_and_forecast
  fixtures: []
  markers: []
notes:
  behavior: Merges present and forecast values into interval results.
  redundancy: Unit-level coverage of load logic.
  decision_rationale: Keep. Validates internal load path.
---

# Behavior summary

Load merges present and forecast data and returns interval values.

# Redundancy / overlap

Complementary to integration load test.

# Decision rationale

Keep. Unit coverage is valuable.

# Fixtures / setup

Uses monkeypatched load_sensors.

# Next actions

None.

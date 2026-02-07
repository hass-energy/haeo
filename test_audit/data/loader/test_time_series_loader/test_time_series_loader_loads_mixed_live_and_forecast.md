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
  nodeid: tests/data/loader/test_time_series_loader.py::test_time_series_loader_loads_mixed_live_and_forecast
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_time_series_loader_loads_mixed_live_and_forecast
  fixtures: []
  markers: []
notes:
  behavior: Combines live and forecast sensor data into horizon-aligned interval values.
  redundancy: Integration-level load behavior.
  decision_rationale: Keep. Validates real HA state integration.
---

# Behavior summary

Live values and forecast series are fused into interval outputs.

# Redundancy / overlap

Complements unit tests by using HA state.

# Decision rationale

Keep. Integration-level coverage is important.

# Fixtures / setup

Mocks extractor and HA state.

# Next actions

None.

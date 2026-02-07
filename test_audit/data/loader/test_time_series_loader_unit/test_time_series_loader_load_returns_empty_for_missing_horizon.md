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
  nodeid: tests/data/loader/test_time_series_loader_unit.py::test_time_series_loader_load_returns_empty_for_missing_horizon
  source_file: tests/data/loader/test_time_series_loader_unit.py
  test_class: ''
  test_function: test_time_series_loader_load_returns_empty_for_missing_horizon
  fixtures: []
  markers: []
notes:
  behavior: Returns empty list when forecast_times is empty.
  redundancy: Unit-level empty-horizon coverage.
  decision_rationale: Keep. Empty horizons should short-circuit.
---

# Behavior summary

Empty forecast horizons yield empty results.

# Redundancy / overlap

Overlaps integration empty-horizon test but at unit level.

# Decision rationale

Keep. Unit-level guard behavior.

# Fixtures / setup

Uses Home Assistant fixture.

# Next actions

None.

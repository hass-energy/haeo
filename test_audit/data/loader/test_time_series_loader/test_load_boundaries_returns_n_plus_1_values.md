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
  nodeid: tests/data/loader/test_time_series_loader.py::test_load_boundaries_returns_n_plus_1_values
  source_file: tests/data/loader/test_time_series_loader.py
  test_class: ''
  test_function: test_load_boundaries_returns_n_plus_1_values
  fixtures: []
  markers: []
notes:
  behavior: Boundary loader returns one value per boundary timestamp.
  redundancy: Unique boundary integration path.
  decision_rationale: Keep. Boundary loading is distinct from interval loading.
---

# Behavior summary

load_boundaries returns n+1 values aligned to boundary timestamps.

# Redundancy / overlap

Distinct from interval load tests.

# Decision rationale

Keep. Boundary loader needs coverage.

# Fixtures / setup

Mocks extractor and HA state.

# Next actions

None.

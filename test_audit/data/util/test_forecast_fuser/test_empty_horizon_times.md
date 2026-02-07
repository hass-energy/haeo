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
  nodeid: tests/data/util/test_forecast_fuser.py::test_empty_horizon_times
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_empty_horizon_times
  fixtures: []
  markers: []
notes:
  behavior: Returns empty list when horizon times are empty.
  redundancy: Distinct for interval fusion helper.
  decision_rationale: Keep. Empty horizon should short-circuit.
---

# Behavior summary

Empty horizons return empty interval results.

# Redundancy / overlap

Separate from boundary empty-horizon test.

# Decision rationale

Keep. Ensures safe empty-horizon handling.

# Fixtures / setup

None.

# Next actions

None.

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
  nodeid: tests/data/util/test_forecast_fuser.py::test_fuse_to_boundaries_empty_horizon
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_fuse_to_boundaries_empty_horizon
  fixtures: []
  markers: []
notes:
  behavior: Returns empty list for empty boundary horizons.
  redundancy: Distinct for boundary fusion helper.
  decision_rationale: Keep. Empty boundary horizon should short-circuit.
---

# Behavior summary

Empty horizons return empty boundary results.

# Redundancy / overlap

Separate from interval empty-horizon test.

# Decision rationale

Keep. Ensures safe empty-horizon handling.

# Fixtures / setup

None.

# Next actions

None.

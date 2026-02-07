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
  nodeid: tests/data/util/test_forecast_fuser.py::test_fuse_to_boundaries_raises_when_no_data
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_fuse_to_boundaries_raises_when_no_data
  fixtures: []
  markers: []
notes:
  behavior: Raises ValueError when both forecast and present are missing (boundary fusion).
  redundancy: Distinct boundary error path.
  decision_rationale: Keep. Ensures error for missing inputs.
---

# Behavior summary

Missing forecast and present value raises for boundary fusion.

# Redundancy / overlap

Separate from interval fusion error test.

# Decision rationale

Keep. Boundary path should fail fast.

# Fixtures / setup

None.

# Next actions

None.

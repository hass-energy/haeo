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
  nodeid: tests/data/util/test_forecast_fuser.py::test_fuse_to_boundaries
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_fuse_to_boundaries
  fixtures: []
  markers: []
notes:
  behavior: Fuses present and forecast values into boundary-aligned values with interpolation.
  redundancy: Distinct boundary fusion behavior.
  decision_rationale: Keep. Required for boundary loader.
---

# Behavior summary

Parameterized test covers boundary interpolation and present override cases.

# Redundancy / overlap

Distinct from interval fusion tests.

# Decision rationale

Keep. Boundary fusion must be validated.

# Fixtures / setup

None.

# Next actions

None.

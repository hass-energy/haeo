---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/data/util/test_forecast_fuser.py::test_fuse_to_boundaries_present_only
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_fuse_to_boundaries_present_only
  fixtures: []
  markers: []
notes:
  behavior: Present-only boundaries repeat present value across all boundaries.
  redundancy: Overlaps with parameterized case only_present_value_no_forecast.
  decision_rationale: Combine into parameterized boundary test.
---

# Behavior summary

Present-only inputs return constant boundary values.

# Redundancy / overlap

Covered by parameterized only_present_value_no_forecast case.

# Decision rationale

Combine. Reduce duplication.

# Fixtures / setup

None.

# Next actions

Consider removing if parameterized case retained.

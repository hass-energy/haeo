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
  nodeid: tests/data/util/test_forecast_fuser.py::test_fuse_to_intervals
  source_file: tests/data/util/test_forecast_fuser.py
  test_class: ''
  test_function: test_fuse_to_intervals
  fixtures: []
  markers: []
notes:
  behavior: Fuses present values with forecast data into interval-aligned values using interpolation.
  redundancy: Complementary to boundary fusion coverage.
  decision_rationale: Keep. Core interval fusion behavior.
---

# Behavior summary

Validates interval fusion for present overrides, interpolation, and cycling cases.

# Redundancy / overlap

Distinct from boundary fusion tests.

# Decision rationale

Keep. Interval fusion is core data preparation logic.

# Fixtures / setup

None.

# Next actions

None.

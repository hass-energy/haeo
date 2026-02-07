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
  nodeid: tests/entities/test_haeo_number.py::test_horizon_start_returns_first_timestamp
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_horizon_start_returns_first_timestamp
  fixtures: []
  markers: []
notes:
  behavior: horizon_start returns first timestamp after forecast update.
  redundancy: Core forecast behavior.
  decision_rationale: Keep. Validates forecast start handling.
---

# Behavior summary

Returns first horizon timestamp when forecast exists.

# Redundancy / overlap

Complementary to None-without-forecast test.

# Decision rationale

Keep. Ensures horizon start reporting.

# Fixtures / setup

Uses editable forecast update.

# Next actions

None.

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
  nodeid: tests/entities/test_haeo_switch.py::test_get_values_returns_forecast_values
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_get_values_returns_forecast_values
  fixtures: []
  markers: []
notes:
  behavior: get_values returns forecast values for switch.
  redundancy: Core forecast retrieval.
  decision_rationale: Keep. Ensures values exposure.
---

# Behavior summary

Returns tuple of forecast values.

# Redundancy / overlap

Complementary to None-without-forecast test.

# Decision rationale

Keep. Validates forecast output.

# Fixtures / setup

Uses forecast update.

# Next actions

None.

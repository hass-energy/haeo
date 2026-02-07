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
  nodeid: tests/entities/test_haeo_number.py::test_get_values_returns_forecast_values
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_get_values_returns_forecast_values
  fixtures: []
  markers: []
notes:
  behavior: get_values returns forecast values for editable fields.
  redundancy: Core forecast retrieval.
  decision_rationale: Keep. Ensures values expose correct forecast.
---

# Behavior summary

Returns tuple of forecast interval values.

# Redundancy / overlap

Complementary to None/percentage tests.

# Decision rationale

Keep. Validates forecast output.

# Fixtures / setup

Uses editable forecast update.

# Next actions

None.

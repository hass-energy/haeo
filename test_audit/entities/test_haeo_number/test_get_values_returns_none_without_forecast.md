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
  nodeid: tests/entities/test_haeo_number.py::test_get_values_returns_none_without_forecast
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_get_values_returns_none_without_forecast
  fixtures: []
  markers: []
notes:
  behavior: get_values returns None when forecast attributes missing.
  redundancy: Companion to values-present test.
  decision_rationale: Keep. Ensures None handling.
---

# Behavior summary

Returns None when forecast data is absent.

# Redundancy / overlap

Complementary to forecast values tests.

# Decision rationale

Keep. Ensures safe None handling.

# Fixtures / setup

Clears forecast attributes.

# Next actions

None.

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
  nodeid: tests/entities/test_haeo_switch.py::test_get_values_returns_none_without_forecast
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_get_values_returns_none_without_forecast
  fixtures: []
  markers: []
notes:
  behavior: get_values returns None when forecast data is missing.
  redundancy: Companion to forecast values test.
  decision_rationale: Keep. Ensures None handling.
---

# Behavior summary

Returns None without forecast data.

# Redundancy / overlap

Complementary to forecast values test.

# Decision rationale

Keep. Ensures safe None handling.

# Fixtures / setup

Clears forecast attributes.

# Next actions

None.

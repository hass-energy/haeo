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
  nodeid: tests/entities/test_haeo_switch.py::test_horizon_start_returns_none_without_forecast
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_horizon_start_returns_none_without_forecast
  fixtures: []
  markers: []
notes:
  behavior: horizon_start returns None when forecast is missing.
  redundancy: Companion to horizon start present test.
  decision_rationale: Keep. Ensures None handling.
---

# Behavior summary

Returns None without forecast data.

# Redundancy / overlap

Complementary to horizon-start present test.

# Decision rationale

Keep. Ensures safe None handling.

# Fixtures / setup

Clears forecast attributes.

# Next actions

None.

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
  nodeid: tests/elements/connection/test_adapter.py::test_available_returns_false_when_optional_sensor_missing
  source_file: tests/elements/connection/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_optional_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when an optional configured sensor is missing.
  redundancy: Optional sensor guard.
  decision_rationale: Keep. Missing configured sensors should fail.
---

# Behavior summary

Configured optional sensor missing makes availability false.

# Redundancy / overlap

Pairs with optional sensor exists test.

# Decision rationale

Keep. Optional sensor guard is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

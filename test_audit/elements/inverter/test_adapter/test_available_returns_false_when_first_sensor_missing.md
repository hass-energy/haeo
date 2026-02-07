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
  nodeid: tests/elements/inverter/test_adapter.py::test_available_returns_false_when_first_sensor_missing
  source_file: tests/elements/inverter/test_adapter.py
  test_class: ''
  test_function: test_available_returns_false_when_first_sensor_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability fails when first limit sensor is missing.
  redundancy: Missing-sensor guard.
  decision_rationale: Keep. Required sensors must be enforced.
---

# Behavior summary

Missing dc-to-ac limit sensor makes availability false.

# Redundancy / overlap

Distinct from second-sensor missing case.

# Decision rationale

Keep. Availability guard is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

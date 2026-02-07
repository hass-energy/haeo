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
  nodeid: tests/elements/connection/test_adapter.py::test_available_returns_true_when_optional_sensors_exist
  source_file: tests/elements/connection/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_when_optional_sensors_exist
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds when optional sensors are configured and present.
  redundancy: Optional sensor coverage.
  decision_rationale: Keep. Optional sensors should be supported.
---

# Behavior summary

Optional sensor configuration is accepted when sensors exist.

# Redundancy / overlap

Pairs with missing optional sensor test.

# Decision rationale

Keep. Optional sensor behavior is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

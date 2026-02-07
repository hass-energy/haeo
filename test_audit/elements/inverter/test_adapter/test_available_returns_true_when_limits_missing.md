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
  nodeid: tests/elements/inverter/test_adapter.py::test_available_returns_true_when_limits_missing
  source_file: tests/elements/inverter/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_when_limits_missing
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds when limits are omitted.
  redundancy: Optional limits branch.
  decision_rationale: Keep. Limits are optional.
---

# Behavior summary

Omitted limit sensors are allowed for availability.

# Redundancy / overlap

No overlap with missing-sensor cases.

# Decision rationale

Keep. Optional limits should not block availability.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

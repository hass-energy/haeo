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
  nodeid: tests/elements/connection/test_adapter.py::test_available_returns_true_with_constant_values
  source_file: tests/elements/connection/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true_with_constant_values
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds when values are constants.
  redundancy: Constant-value path.
  decision_rationale: Keep. Constants should bypass sensor checks.
---

# Behavior summary

Constant values do not block availability.

# Redundancy / overlap

No overlap with sensor-based cases.

# Decision rationale

Keep. Constant handling is important.

# Fixtures / setup

None.

# Next actions

None.

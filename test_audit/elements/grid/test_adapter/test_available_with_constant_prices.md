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
  nodeid: tests/elements/grid/test_adapter.py::test_available_with_constant_prices
  source_file: tests/elements/grid/test_adapter.py
  test_class: ''
  test_function: test_available_with_constant_prices
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds when prices are constants.
  redundancy: Constant-value path.
  decision_rationale: Keep. Constants should bypass sensor checks.
---

# Behavior summary

Constant prices do not block availability.

# Redundancy / overlap

No overlap with sensor-based cases.

# Decision rationale

Keep. Constant handling is important.

# Fixtures / setup

None.

# Next actions

None.

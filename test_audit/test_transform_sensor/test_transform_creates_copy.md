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
  nodeid: tests/test_transform_sensor.py::test_transform_creates_copy
  source_file: tests/test_transform_sensor.py
  test_class: ''
  test_function: test_transform_creates_copy
  fixtures: []
  markers: []
notes:
  behavior: Ensures forecast timestamp transform returns a new dict and leaves input unchanged.
  redundancy: Unique immutability check.
  decision_rationale: Keep. Guards against in-place mutation.
---

# Behavior summary

Verifies transformed forecasts are copies and the original forecast dict is unchanged.

# Redundancy / overlap

No overlap with value transformation tests.

# Decision rationale

Keep. Immutability is important for caller safety.

# Fixtures / setup

None.

# Next actions

None.

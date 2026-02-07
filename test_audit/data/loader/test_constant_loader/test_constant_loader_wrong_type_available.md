---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/data/loader/test_constant_loader.py::test_constant_loader_wrong_type_available
  source_file: tests/data/loader/test_constant_loader.py
  test_class: ''
  test_function: test_constant_loader_wrong_type_available
  fixtures: []
  markers: []
notes:
  behavior: Available raises TypeError for wrong value type.
  redundancy: Overlaps with wrong-type load test.
  decision_rationale: Combine wrong-type available/load into one parameterized test.
---

# Behavior summary

Available raises TypeError for invalid value types.

# Redundancy / overlap

Overlaps with wrong-type load test.

# Decision rationale

Combine with wrong-type load test.

# Fixtures / setup

Uses Home Assistant fixture.

# Next actions

Consider parameterizing wrong-type tests.

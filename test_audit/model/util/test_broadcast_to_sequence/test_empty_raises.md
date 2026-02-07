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
  nodeid: tests/model/util/test_broadcast_to_sequence.py::test_empty_raises
  source_file: tests/model/util/test_broadcast_to_sequence.py
  test_class: ''
  test_function: test_empty_raises
  fixtures: []
  markers: []
notes:
  behavior: Empty sequences raise appropriate errors.
  redundancy: Complementary to broadcast and truncate tests.
  decision_rationale: Keep. Ensures invalid inputs are rejected.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

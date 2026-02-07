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
  nodeid: tests/entities/test_haeo_number.py::test_entity_does_not_poll
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_entity_does_not_poll
  fixtures: []
  markers: []
notes:
  behavior: Number entity does not poll.
  redundancy: Simple metadata check.
  decision_rationale: Keep. Ensures polling config is correct.
---

# Behavior summary

Entity has `should_poll` set to False.

# Redundancy / overlap

Simple metadata check.

# Decision rationale

Keep. Prevents polling regression.

# Fixtures / setup

Uses subentry with constant value.

# Next actions

None.

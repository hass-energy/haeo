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
  nodeid: tests/elements/grid/test_flow.py::test_user_step_with_constant_creates_entry
  source_file: tests/elements/grid/test_flow.py
  test_class: ''
  test_function: test_user_step_with_constant_creates_entry
  fixtures: []
  markers: []
notes:
  behavior: User flow with constant values creates entry with constants.
  redundancy: Core grid flow behavior.
  decision_rationale: Keep. Validates constant handling.
---

# Behavior summary

Constant values are stored as schema constants in created entry.

# Redundancy / overlap

Distinct from entity-value user flow test.

# Decision rationale

Keep. Constant handling should be validated.

# Fixtures / setup

Uses hub entry and participant setup.

# Next actions

None.

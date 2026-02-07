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
  nodeid: tests/elements/load/test_flow.py::test_reconfigure_with_scalar_shows_constant_defaults
  source_file: tests/elements/load/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_scalar_shows_constant_defaults
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure defaults show constant choice for scalar values.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared defaults tests.
---

# Behavior summary

Scalar defaults map to constant choice in reconfigure.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate defaults behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating defaults tests.

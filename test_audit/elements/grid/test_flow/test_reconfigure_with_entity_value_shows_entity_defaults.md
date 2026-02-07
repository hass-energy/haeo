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
  nodeid: tests/elements/grid/test_flow.py::test_reconfigure_with_entity_value_shows_entity_defaults
  source_file: tests/elements/grid/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_entity_value_shows_entity_defaults
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure defaults preserve entity values.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared defaults tests.
---

# Behavior summary

Entity values are preserved as defaults during reconfigure.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate defaults behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating defaults tests.

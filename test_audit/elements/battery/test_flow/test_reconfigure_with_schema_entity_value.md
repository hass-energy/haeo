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
  nodeid: tests/elements/battery/test_flow.py::test_reconfigure_with_schema_entity_value
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_schema_entity_value
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure defaults preserve entity IDs from schema values.
  redundancy: Pattern repeated across element flow tests.
  decision_rationale: Combine into shared reconfigure default tests.
---

# Behavior summary

Reconfigure defaults preserve schema entity values.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared reconfigure default behavior.

# Fixtures / setup

Uses hub entry and existing subentry.

# Next actions

Consider consolidating reconfigure defaults tests.

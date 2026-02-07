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
  nodeid: tests/elements/battery/test_flow.py::test_defaults_with_entity_strings_shows_entity_choice
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_defaults_with_entity_strings_shows_entity_choice
  fixtures: []
  markers: []
notes:
  behavior: Defaults show entity choice for entity schema values.
  redundancy: Pattern repeated across element flow tests.
  decision_rationale: Combine into shared flow defaults tests.
---

# Behavior summary

Entity values default to entity selection in flow defaults.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared defaults behavior.

# Fixtures / setup

Uses flow defaults builder.

# Next actions

Consider consolidating defaults tests.

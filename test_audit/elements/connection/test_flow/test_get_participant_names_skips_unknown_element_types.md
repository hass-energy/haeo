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
  nodeid: tests/elements/connection/test_flow.py::test_get_participant_names_skips_unknown_element_types
  source_file: tests/elements/connection/test_flow.py
  test_class: ''
  test_function: test_get_participant_names_skips_unknown_element_types
  fixtures: []
  markers: []
notes:
  behavior: Skips unknown element types when listing participants.
  redundancy: Repeated across element flow tests.
  decision_rationale: Combine into shared flow behavior tests.
---

# Behavior summary

Unknown element types are ignored when listing participants.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared flow behavior.

# Fixtures / setup

Uses hub entry and subentries.

# Next actions

Consider consolidating into shared flow test.

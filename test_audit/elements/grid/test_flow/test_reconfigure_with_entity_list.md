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
  nodeid: tests/elements/grid/test_flow.py::test_reconfigure_with_entity_list
  source_file: tests/elements/grid/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_entity_list
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure defaults preserve entity lists.
  redundancy: Specific to entity list handling.
  decision_rationale: Keep. Entity list defaults are important.
---

# Behavior summary

Entity ID lists are preserved during reconfigure defaults.

# Redundancy / overlap

Distinct from scalar/entity single-value defaults.

# Decision rationale

Keep. Entity list handling should be validated.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

None.

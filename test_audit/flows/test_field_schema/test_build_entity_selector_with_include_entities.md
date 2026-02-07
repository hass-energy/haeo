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
  nodeid: tests/flows/test_field_schema.py::test_build_entity_selector_with_include_entities
  source_file: tests/flows/test_field_schema.py
  test_class: ''
  test_function: test_build_entity_selector_with_include_entities
  fixtures: []
  markers: []
notes:
  behavior: Validates field_schema helper behavior.
  redundancy: Unit coverage for schema utilities.
  decision_rationale: Keep. Prevent regressions in field schema helpers.
---

# Behavior summary

Validates field_schema helper behavior.

# Redundancy / overlap

Unit-level coverage for schema utilities.

# Decision rationale

Keep. Core helper behavior.

# Fixtures / setup

Uses field_schema helper inputs.

# Next actions

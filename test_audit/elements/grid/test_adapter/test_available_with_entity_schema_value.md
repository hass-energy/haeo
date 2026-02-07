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
  nodeid: tests/elements/grid/test_adapter.py::test_available_with_entity_schema_value
  source_file: tests/elements/grid/test_adapter.py
  test_class: ''
  test_function: test_available_with_entity_schema_value
  fixtures: []
  markers: []
notes:
  behavior: Availability succeeds with entity schema values.
  redundancy: Base entity-value path.
  decision_rationale: Keep. Entity schema values should be supported.
---

# Behavior summary

Entity schema values are accepted for availability.

# Redundancy / overlap

No overlap with constant-value case.

# Decision rationale

Keep. Entity handling is important.

# Fixtures / setup

Uses Home Assistant state fixtures.

# Next actions

None.

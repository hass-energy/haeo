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
  nodeid: tests/test_diagnostics.py::test_diagnostics_skips_driven_entity_values
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_skips_driven_entity_values
  fixtures: []
  markers: []
notes:
  behavior: Keeps driven entity config values instead of replacing them with runtime values.
  redundancy: Distinct from editable entity behavior.
  decision_rationale: Keep. Driven entities should preserve config values.
---

# Behavior summary

Driven entity values remain unchanged in diagnostics.

# Redundancy / overlap

No overlap with editable entity test.

# Decision rationale

Keep. Driven entity behavior is distinct.

# Fixtures / setup

Uses Home Assistant fixtures and mock entities.

# Next actions

None.

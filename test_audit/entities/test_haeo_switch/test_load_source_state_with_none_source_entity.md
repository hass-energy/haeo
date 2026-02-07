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
  nodeid: tests/entities/test_haeo_switch.py::test_load_source_state_with_none_source_entity
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_load_source_state_with_none_source_entity
  fixtures: []
  markers: []
notes:
  behavior: Load source state returns early when source entity is None.
  redundancy: Editable-mode safeguard.
  decision_rationale: Keep. Ensures no errors when no source entity.
---

# Behavior summary

`_load_source_state()` is a no-op in editable mode.

# Redundancy / overlap

Distinct from driven load tests.

# Decision rationale

Keep. Protects editable behavior.

# Fixtures / setup

Uses editable subentry.

# Next actions

None.

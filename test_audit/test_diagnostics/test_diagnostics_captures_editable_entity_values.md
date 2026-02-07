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
  nodeid: tests/test_diagnostics.py::test_diagnostics_captures_editable_entity_values
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_captures_editable_entity_values
  fixtures: []
  markers: []
notes:
  behavior: Replaces editable entity config values with current runtime values.
  redundancy: Related to driven/None-value tests but distinct case.
  decision_rationale: Keep. Ensures editable entities use runtime state.
---

# Behavior summary

Editable entities are reported using current entity state values in diagnostics.

# Redundancy / overlap

No overlap with driven or None-value cases.

# Decision rationale

Keep. Editable entity handling is required.

# Fixtures / setup

Uses Home Assistant fixtures and mock entities.

# Next actions

None.

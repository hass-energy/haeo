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
  nodeid: tests/test_diagnostics.py::test_diagnostics_skips_switch_with_none_value
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_skips_switch_with_none_value
  fixtures: []
  markers: []
notes:
  behavior: Skips editable entity value when runtime state is None.
  redundancy: Related to editable/driven entity tests but distinct None-value path.
  decision_rationale: Keep. None-value handling is important.
---

# Behavior summary

Ensures diagnostics do not replace editable config values when the runtime value is None.

# Redundancy / overlap

No overlap with editable/driven tests; this is a None-value case.

# Decision rationale

Keep. Protects against None runtime values.

# Fixtures / setup

Uses Home Assistant fixtures and mock entities.

# Next actions

Consider aligning test name with actual entity type if desired.

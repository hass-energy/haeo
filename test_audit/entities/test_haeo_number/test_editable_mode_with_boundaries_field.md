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
  nodeid: tests/entities/test_haeo_number.py::test_editable_mode_with_boundaries_field
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_editable_mode_with_boundaries_field
  fixtures: []
  markers: []
notes:
  behavior: Boundaries fields produce n+1 forecast values and scale percent.
  redundancy: Specific to boundaries behavior.
  decision_rationale: Keep. Ensures boundary handling.
---

# Behavior summary

Editable forecast for boundaries fields yields n+1 values.

# Redundancy / overlap

Distinct from interval forecast tests.

# Decision rationale

Keep. Protects boundary logic.

# Fixtures / setup

Uses boundary field info.

# Next actions

None.

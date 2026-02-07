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
  nodeid: tests/entities/test_haeo_horizon.py::test_entity_category_is_diagnostic
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_entity_category_is_diagnostic
  fixtures: []
  markers: []
notes:
  behavior: Horizon entity is diagnostic category.
  redundancy: Simple metadata check.
  decision_rationale: Keep. Ensures entity metadata.
---

# Behavior summary

Entity category is `DIAGNOSTIC`.

# Redundancy / overlap

Simple metadata check.

# Decision rationale

Keep. Prevents category regressions.

# Fixtures / setup

Uses horizon entity.

# Next actions

None.

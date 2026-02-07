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
  nodeid: tests/entities/test_haeo_switch.py::test_entity_has_correct_category
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_entity_has_correct_category
  fixtures: []
  markers: []
notes:
  behavior: Switch entity is config category.
  redundancy: Simple metadata check.
  decision_rationale: Keep. Ensures entity metadata.
---

# Behavior summary

Entity category is `CONFIG`.

# Redundancy / overlap

Simple metadata check.

# Decision rationale

Keep. Prevents category regressions.

# Fixtures / setup

Uses switch entity.

# Next actions

None.

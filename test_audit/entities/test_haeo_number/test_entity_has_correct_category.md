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
  nodeid: tests/entities/test_haeo_number.py::test_entity_has_correct_category
  source_file: tests/entities/test_haeo_number.py
  test_class: ''
  test_function: test_entity_has_correct_category
  fixtures: []
  markers: []
notes:
  behavior: Number entity is categorized as config.
  redundancy: Small, but verifies entity metadata.
  decision_rationale: Keep. Confirms entity category.
---

# Behavior summary

Entity category is `CONFIG`.

# Redundancy / overlap

Simple metadata check.

# Decision rationale

Keep. Prevents metadata regressions.

# Fixtures / setup

Uses subentry with constant value.

# Next actions

None.

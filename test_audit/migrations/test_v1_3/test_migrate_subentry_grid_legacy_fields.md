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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_grid_legacy_fields
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_grid_legacy_fields
  fixtures: []
  markers: []
notes:
  behavior: Maps legacy grid import/export fields into pricing and power limit sections.
  redundancy: Only test covering grid legacy field mapping.
  decision_rationale: Keep to enforce grid migration compatibility.
---

# Behavior summary

Asserts legacy grid fields are migrated into sectioned pricing and power limit values.

# Redundancy / overlap

Unique coverage for grid legacy field mapping.

# Decision rationale

Keep. This is the grid migration path.

# Fixtures / setup

None.

# Next actions

None.

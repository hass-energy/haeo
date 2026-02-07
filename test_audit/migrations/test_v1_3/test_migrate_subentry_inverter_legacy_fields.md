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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_inverter_legacy_fields
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_inverter_legacy_fields
  fixtures: []
  markers: []
notes:
  behavior: Maps legacy inverter fields into power limit and efficiency sections.
  redundancy: Only test covering inverter legacy migration mapping.
  decision_rationale: Keep to validate inverter migration path.
---

# Behavior summary

Asserts legacy inverter fields are migrated into sectioned limits and efficiency values.

# Redundancy / overlap

Unique coverage for inverter legacy mapping.

# Decision rationale

Keep. Ensures inverter migration correctness.

# Fixtures / setup

None.

# Next actions

None.

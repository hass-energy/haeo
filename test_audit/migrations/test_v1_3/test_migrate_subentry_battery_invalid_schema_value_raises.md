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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_battery_invalid_schema_value_raises
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_battery_invalid_schema_value_raises
  fixtures: []
  markers: []
notes:
  behavior: Ensures battery migration rejects unsupported schema value types.
  redundancy: Only test asserting TypeError for invalid schema value during migration.
  decision_rationale: Keep to enforce strict schema handling.
---

# Behavior summary

Asserts \_migrate_subentry_data raises TypeError for invalid battery schema value types.

# Redundancy / overlap

Unique error-path coverage.

# Decision rationale

Keep. Validates migration guardrails on schema value types.

# Fixtures / setup

None.

# Next actions

None.

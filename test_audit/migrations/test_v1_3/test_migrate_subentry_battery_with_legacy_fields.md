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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_subentry_battery_with_legacy_fields
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_subentry_battery_with_legacy_fields
  fixtures: []
  markers: []
notes:
  behavior: Maps legacy battery fields into sectioned data with proper value coercion.
  redundancy: No other test covers battery legacy fields plus section overrides together.
  decision_rationale: Validates complex battery migration mapping; critical for backward compatibility.
---

# Behavior summary

Asserts legacy battery fields and existing section values are migrated into sectioned data with constant/value wrappers.

# Redundancy / overlap

Unique coverage for battery legacy field migration and section precedence.

# Decision rationale

Keep. Protects the most complex element migration path.

# Fixtures / setup

None.

# Next actions

None.

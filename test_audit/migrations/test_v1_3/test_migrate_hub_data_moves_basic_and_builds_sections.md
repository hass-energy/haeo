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
  nodeid: tests/migrations/test_v1_3.py::test_migrate_hub_data_moves_basic_and_builds_sections
  source_file: tests/migrations/test_v1_3.py
  test_class: ''
  test_function: test_migrate_hub_data_moves_basic_and_builds_sections
  fixtures: []
  markers: []
notes:
  behavior: Validates hub data migration moves legacy fields into sectioned data and clears legacy keys/options.
  redundancy: No other test asserts full hub section build with both data and options.
  decision_rationale: Core migration behavior for hub entries; must keep.
---

# Behavior summary

Asserts that legacy hub fields and options are moved into sectioned data and that legacy keys/options are removed.

# Redundancy / overlap

Unique coverage for full hub data migration transformation.

# Decision rationale

Keep. It guards the primary hub migration path in v1.3.

# Fixtures / setup

None.

# Next actions

None.

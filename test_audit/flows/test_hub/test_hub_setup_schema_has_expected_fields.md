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
  nodeid: tests/flows/test_hub.py::test_hub_setup_schema_has_expected_fields
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_hub_setup_schema_has_expected_fields
  fixtures: []
  markers: []
notes:
  behavior: Hub setup schema includes expected fields and excludes tier fields.
  redundancy: Schema structure coverage.
  decision_rationale: Keep. Ensures correct hub setup schema.
---

# Behavior summary

Simplified hub schema exposes name and preset without tier fields.

# Redundancy / overlap

Complementary to custom tiers schema tests.

# Decision rationale

Keep. Prevents schema regressions.

# Fixtures / setup

Uses hub setup schema helper.

# Next actions

None.

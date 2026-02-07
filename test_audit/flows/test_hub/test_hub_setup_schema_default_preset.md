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
  nodeid: tests/flows/test_hub.py::test_hub_setup_schema_default_preset
  source_file: tests/flows/test_hub.py
  test_class: ''
  test_function: test_hub_setup_schema_default_preset
  fixtures: []
  markers: []
notes:
  behavior: Hub setup schema defaults to 5-day horizon preset.
  redundancy: Default behavior coverage.
  decision_rationale: Keep. Ensures default preset stays consistent.
---

# Behavior summary

Horizon preset default is 5 days.

# Redundancy / overlap

Distinct from schema field presence tests.

# Decision rationale

Keep. Prevents default regressions.

# Fixtures / setup

Uses hub setup schema helper.

# Next actions

None.

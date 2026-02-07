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
  nodeid: tests/schema/test_connection_target.py::test_normalize_connection_target_handles_str_and_schema_value
  source_file: tests/schema/test_connection_target.py
  test_class: ''
  test_function: test_normalize_connection_target_handles_str_and_schema_value
  fixtures: []
  markers: []
notes:
  behavior: Normalizes string and schema-value inputs into a target name.
  redundancy: Complements invalid-type rejection test.
  decision_rationale: Keep. Core normalization helper coverage.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

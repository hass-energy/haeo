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
  nodeid: tests/schema/test_connection_target.py::test_get_connection_target_name_rejects_invalid_type
  source_file: tests/schema/test_connection_target.py
  test_class: ''
  test_function: test_get_connection_target_name_rejects_invalid_type
  fixtures: []
  markers: []
notes:
  behavior: Rejects invalid types when resolving connection target names.
  redundancy: Complements normalization and mapping checks.
  decision_rationale: Keep. Guards against bad input types.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

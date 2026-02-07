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
  nodeid: tests/schema/test_connection_target.py::test_normalize_connection_target_rejects_invalid_type
  source_file: tests/schema/test_connection_target.py
  test_class: ''
  test_function: test_normalize_connection_target_rejects_invalid_type
  fixtures: []
  markers: []
notes:
  behavior: Rejects invalid types when normalizing connection targets.
  redundancy: Distinct from normalization success paths.
  decision_rationale: Keep. Protects input validation behavior.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

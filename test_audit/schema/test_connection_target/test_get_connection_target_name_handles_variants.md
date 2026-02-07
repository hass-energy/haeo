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
  nodeid: tests/schema/test_connection_target.py::test_get_connection_target_name_handles_variants
  source_file: tests/schema/test_connection_target.py
  test_class: ''
  test_function: test_get_connection_target_name_handles_variants
  fixtures: []
  markers: []
notes:
  behavior: Normalizes connection target names across schema value variants.
  redundancy: No overlap with invalid-type rejection tests.
  decision_rationale: Keep. Ensures target name normalization remains stable.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

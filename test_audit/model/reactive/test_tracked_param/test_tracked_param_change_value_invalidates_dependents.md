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
  nodeid: tests/model/reactive/test_tracked_param.py::test_tracked_param_change_value_invalidates_dependents
  source_file: tests/model/reactive/test_tracked_param.py
  test_class: ''
  test_function: test_tracked_param_change_value_invalidates_dependents
  fixtures: []
  markers: []
notes:
  behavior: Changing tracked param invalidates dependent reactive outputs.
  redundancy: Distinct from same-value no-invalidate test.
  decision_rationale: Keep. Dependency invalidation is core.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

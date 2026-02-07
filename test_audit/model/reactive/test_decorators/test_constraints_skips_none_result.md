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
  nodeid: tests/model/reactive/test_decorators.py::test_constraints_skips_none_result
  source_file: tests/model/reactive/test_decorators.py
  test_class: ''
  test_function: test_constraints_skips_none_result
  fixtures: []
  markers: []
notes:
  behavior: Skips constraint entries when reactive decorator returns None.
  redundancy: Distinct from add-new-constraint test.
  decision_rationale: Keep. Ensures None results are ignored.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

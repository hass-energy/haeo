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
  nodeid: tests/model/test_network.py::test_network_optimize_constraints_error
  source_file: tests/model/test_network.py
  test_class: ''
  test_function: test_network_optimize_constraints_error
  fixtures: []
  markers: []
notes:
  behavior: Optimization raises when constraint creation fails.
  redundancy: Complementary to solver/infeasible errors.
  decision_rationale: Keep. Ensures errors surface.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

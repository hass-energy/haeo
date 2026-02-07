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
  nodeid: tests/model/test_network.py::test_network_optimize_raises_on_solver_failure
  source_file: tests/model/test_network.py
  test_class: ''
  test_function: test_network_optimize_raises_on_solver_failure
  fixtures: []
  markers: []
notes:
  behavior: Optimization raises on solver failure.
  redundancy: Complementary to infeasible and constraints error tests.
  decision_rationale: Keep. Ensures solver errors surface.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

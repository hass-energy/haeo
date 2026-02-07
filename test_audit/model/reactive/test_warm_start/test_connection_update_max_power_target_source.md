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
  nodeid: tests/model/reactive/test_warm_start.py::test_connection_update_max_power_target_source
  source_file: tests/model/reactive/test_warm_start.py
  test_class: ''
  test_function: test_connection_update_max_power_target_source
  fixtures: []
  markers: []
notes:
  behavior: Updating connection max power (target→source) rebuilds constraints.
  redundancy: Complementary to source→target update tests.
  decision_rationale: Keep. Ensures warm-start update behavior.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

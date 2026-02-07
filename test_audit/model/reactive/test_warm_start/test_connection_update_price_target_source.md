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
  nodeid: tests/model/reactive/test_warm_start.py::test_connection_update_price_target_source
  source_file: tests/model/reactive/test_warm_start.py
  test_class: ''
  test_function: test_connection_update_price_target_source
  fixtures: []
  markers: []
notes:
  behavior: Updating connection pricing (target→source) rebuilds costs.
  redundancy: Complementary to source→target pricing updates.
  decision_rationale: Keep. Ensures warm-start pricing updates.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

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
  nodeid: tests/model/reactive/test_warm_start.py::test_battery_update_capacity_modifies_soc_constraints
  source_file: tests/model/reactive/test_warm_start.py
  test_class: ''
  test_function: test_battery_update_capacity_modifies_soc_constraints
  fixtures: []
  markers: []
notes:
  behavior: Battery capacity updates rebuild SOC constraints.
  redundancy: Complementary to other battery update tests.
  decision_rationale: Keep. Ensures warm-start constraint updates.
---

# Behavior summary

# Redundancy / overlap

# Decision rationale

# Fixtures / setup

# Next actions

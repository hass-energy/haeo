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
  nodeid: tests/entities/test_haeo_horizon.py::test_horizon_manager_current_start_time
  source_file: tests/entities/test_haeo_horizon.py
  test_class: ''
  test_function: test_horizon_manager_current_start_time
  fixtures: []
  markers: []
notes:
  behavior: HorizonManager current_start_time returns datetime when timestamps set.
  redundancy: Core manager behavior.
  decision_rationale: Keep. Ensures current_start_time works.
---

# Behavior summary

Returns datetime derived from forecast timestamps.

# Redundancy / overlap

Complementary to None case test.

# Decision rationale

Keep. Validates manager property.

# Fixtures / setup

Starts HorizonManager.

# Next actions

None.

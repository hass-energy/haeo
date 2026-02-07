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
  nodeid: tests/entities/test_haeo_switch.py::test_driven_mode_loads_off_state
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_driven_mode_loads_off_state
  fixtures: []
  markers: []
notes:
  behavior: Driven mode loads OFF state from source entity.
  redundancy: Complementary to ON state test.
  decision_rationale: Keep. Ensures source state loads.
---

# Behavior summary

Driven switch reads source state and sets OFF.

# Redundancy / overlap

Pairs with ON-state load test.

# Decision rationale

Keep. Validates source state handling.

# Fixtures / setup

Sets source entity state to OFF.

# Next actions

None.

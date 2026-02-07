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
  nodeid: tests/entities/test_haeo_switch.py::test_driven_mode_loads_source_state
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_driven_mode_loads_source_state
  fixtures: []
  markers: []
notes:
  behavior: Driven mode loads ON state from source entity.
  redundancy: Complementary to OFF state test.
  decision_rationale: Keep. Ensures source state loads.
---

# Behavior summary

Driven switch reads source state and sets ON.

# Redundancy / overlap

Pairs with off-state load test.

# Decision rationale

Keep. Validates source state handling.

# Fixtures / setup

Sets source entity state to ON.

# Next actions

None.

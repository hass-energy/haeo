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
  nodeid: tests/entities/test_haeo_switch.py::test_handle_horizon_change_driven_reloads_source
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_handle_horizon_change_driven_reloads_source
  fixtures: []
  markers: []
notes:
  behavior: Driven horizon change reloads source state and updates horizon start.
  redundancy: Core driven horizon behavior.
  decision_rationale: Keep. Ensures reload occurs.
---

# Behavior summary

Horizon change in driven mode reloads source state.

# Redundancy / overlap

Complementary to driven timestamp write regression test.

# Decision rationale

Keep. Validates driven refresh.

# Fixtures / setup

Sets source state and adds entity.

# Next actions

None.

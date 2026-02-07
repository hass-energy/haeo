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
  nodeid: tests/entities/test_haeo_switch.py::test_wait_ready_blocks_until_data_loaded
  source_file: tests/entities/test_haeo_switch.py
  test_class: ''
  test_function: test_wait_ready_blocks_until_data_loaded
  fixtures: []
  markers: []
notes:
  behavior: wait_ready blocks until driven source state is loaded.
  redundancy: Companion to is_ready test.
  decision_rationale: Keep. Ensures readiness wait behavior.
---

# Behavior summary

`wait_ready()` waits for driven source load before completing.

# Redundancy / overlap

Complementary to readiness flag test.

# Decision rationale

Keep. Validates async wait behavior.

# Fixtures / setup

Uses driven mode and loads source state.

# Next actions

None.

---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/test_switch.py::test_auto_optimize_switch_turn_off
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_auto_optimize_switch_turn_off
  fixtures: []
  markers: []
notes:
  behavior: Turning off clears the switch state and updates underlying coordinator flag.
  redundancy: Symmetric with turn-on test; can be parameterized.
  decision_rationale: Combine with turn-on test into a parameterized on/off case.
---

# Behavior summary

Asserts turning off the auto optimize switch updates the coordinator and entity state.

# Redundancy / overlap

Overlaps with turn-on test.

# Decision rationale

Combine. Parametrize state transitions.

# Fixtures / setup

Uses Home Assistant fixtures and a switch entity.

# Next actions

Consider merging with `test_auto_optimize_switch_turn_on`.

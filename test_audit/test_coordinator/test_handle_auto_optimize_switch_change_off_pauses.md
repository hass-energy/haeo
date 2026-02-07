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
  nodeid: tests/test_coordinator.py::test_handle_auto_optimize_switch_change_off_pauses
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_handle_auto_optimize_switch_change_off_pauses
  fixtures: []
  markers: []
notes:
  behavior: On switch OFF, pauses horizon manager.
  redundancy: Related to ON/None cases but distinct side effects.
  decision_rationale: Keep. OFF transition has side effects.
---

# Behavior summary

Switching auto optimize OFF pauses the horizon manager.

# Redundancy / overlap

Related to ON/None cases but distinct effects.

# Decision rationale

Keep. OFF transition has side effects.

# Fixtures / setup

Mocks switch OFF transition.

# Next actions

None.

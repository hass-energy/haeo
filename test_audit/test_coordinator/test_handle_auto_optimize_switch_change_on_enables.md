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
  nodeid: tests/test_coordinator.py::test_handle_auto_optimize_switch_change_on_enables
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_handle_auto_optimize_switch_change_on_enables
  fixtures: []
  markers: []
notes:
  behavior: On switch ON, resumes horizon and triggers optimization.
  redundancy: Related to OFF/None cases but distinct side effects.
  decision_rationale: Keep. Ensures ON behavior.
---

# Behavior summary

Switching auto optimize ON resumes horizon and triggers refresh.

# Redundancy / overlap

Related to OFF/None cases but distinct effects.

# Decision rationale

Keep. ON transition has side effects.

# Fixtures / setup

Mocks switch ON transition.

# Next actions

None.

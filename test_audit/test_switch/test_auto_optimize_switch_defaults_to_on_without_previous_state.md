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
  nodeid: tests/test_switch.py::test_auto_optimize_switch_defaults_to_on_without_previous_state
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_auto_optimize_switch_defaults_to_on_without_previous_state
  fixtures: []
  markers: []
notes:
  behavior: Defaults to ON when there is no previous state to restore.
  redundancy: Distinct default path; not covered by restore tests.
  decision_rationale: Keep. Validates default state behavior.
---

# Behavior summary

Ensures the switch defaults to ON when no prior state exists.

# Redundancy / overlap

No overlap with restore-on/off cases.

# Decision rationale

Keep. Default behavior is important.

# Fixtures / setup

Uses Home Assistant fixtures and restore state.

# Next actions

None.

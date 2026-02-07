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
  nodeid: tests/test_diagnostics.py::test_diagnostics_with_participants
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_with_participants
  fixtures: []
  markers: []
notes:
  behavior: Includes participant config and input states; outputs empty without coordinator.
  redundancy: Complementary to outputs test.
  decision_rationale: Keep. Validates participant/input diagnostics.
---

# Behavior summary

Ensures diagnostics include participant configs and input states when coordinator is absent.

# Redundancy / overlap

No overlap with output diagnostics case.

# Decision rationale

Keep. Participant/input inclusion is required.

# Fixtures / setup

Uses Home Assistant fixtures and mock entries.

# Next actions

None.

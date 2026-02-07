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
  nodeid: tests/test_repairs.py::test_dismiss_missing_sensor_issue
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_dismiss_missing_sensor_issue
  fixtures: []
  markers: []
notes:
  behavior: Creates and dismisses missing sensor issue, ensuring it is removed.
  redundancy: Pattern similar to other dismiss tests but distinct issue type.
  decision_rationale: Keep. Validates dismissal behavior.
---

# Behavior summary

Ensures missing sensor issue can be dismissed and is removed from registry.

# Redundancy / overlap

No direct overlap beyond dismissal pattern.

# Decision rationale

Keep. Dismissal behavior is required.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.

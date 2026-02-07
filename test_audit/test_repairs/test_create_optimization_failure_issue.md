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
  nodeid: tests/test_repairs.py::test_create_optimization_failure_issue
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_create_optimization_failure_issue
  fixtures: []
  markers: []
notes:
  behavior: Creates optimization failure issue with expected severity and flags.
  redundancy: Translation key also checked elsewhere, but this includes metadata assertions.
  decision_rationale: Keep. Validates issue metadata.
---

# Behavior summary

Ensures optimization failure issue is created with correct flags and severity.

# Redundancy / overlap

Partial overlap with translation key test.

# Decision rationale

Keep. Issue metadata is important.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.

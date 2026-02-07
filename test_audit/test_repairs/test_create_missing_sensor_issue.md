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
  nodeid: tests/test_repairs.py::test_create_missing_sensor_issue
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_create_missing_sensor_issue
  fixtures: []
  markers: []
notes:
  behavior: Creates missing sensor issue with expected severity, fixable, and persistent flags.
  redundancy: Overlap with translation key test but includes full metadata assertions.
  decision_rationale: Keep. Validates issue metadata.
---

# Behavior summary

Ensures missing sensor issue is created with correct flags and severity.

# Redundancy / overlap

Translation key also covered elsewhere, but metadata coverage is unique.

# Decision rationale

Keep. Issue metadata is important.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.

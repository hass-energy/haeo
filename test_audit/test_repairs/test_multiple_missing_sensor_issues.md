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
  nodeid: tests/test_repairs.py::test_multiple_missing_sensor_issues
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_multiple_missing_sensor_issues
  fixtures: []
  markers: []
notes:
  behavior: Creates multiple missing sensor issues and confirms each is registered.
  redundancy: Adds multi-issue coverage beyond single create test.
  decision_rationale: Keep. Validates handling of multiple issues.
---

# Behavior summary

Ensures multiple missing sensor issues can be created and tracked.

# Redundancy / overlap

Some overlap with single missing sensor issue but adds multiplicity.

# Decision rationale

Keep. Multi-issue behavior is distinct.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.

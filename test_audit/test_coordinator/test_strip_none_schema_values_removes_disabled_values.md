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
  nodeid: tests/test_coordinator.py::test_strip_none_schema_values_removes_disabled_values
  source_file: tests/test_coordinator.py
  test_class: ''
  test_function: test_strip_none_schema_values_removes_disabled_values
  fixtures: []
  markers: []
notes:
  behavior: Strips disabled (None) schema values recursively.
  redundancy: Unique helper coverage.
  decision_rationale: Keep. Prevents disabled fields from leaking downstream.
---

# Behavior summary

Recursively removes disabled schema values from config data.

# Redundancy / overlap

No overlap with other tests.

# Decision rationale

Keep. Core helper behavior.

# Fixtures / setup

None.

# Next actions

None.

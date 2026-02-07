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
  nodeid: tests/test_repairs.py::test_create_disconnected_network_issue
  source_file: tests/test_repairs.py
  test_class: ''
  test_function: test_create_disconnected_network_issue
  fixtures: []
  markers: []
notes:
  behavior: Creates disconnected network issue with expected metadata and placeholders.
  redundancy: Unique disconnected network issue coverage.
  decision_rationale: Keep. Validates disconnected network issue details.
---

# Behavior summary

Ensures disconnected network issue is created with severity, flags, translation key, and placeholders.

# Redundancy / overlap

No overlap with other issue types.

# Decision rationale

Keep. Disconnected network handling is unique.

# Fixtures / setup

Uses Home Assistant fixtures and issue registry.

# Next actions

None.

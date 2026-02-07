---
status:
  reviewed: true
  decision: combine
  behavior_documented: true
  redundancy_noted: true
parameterized:
  per_parameter_review: false
  cases: []
meta:
  nodeid: tests/elements/load/test_flow.py::test_reconfigure_with_missing_field_shows_none_default
  source_file: tests/elements/load/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_missing_field_shows_none_default
  fixtures: []
  markers: []
notes:
  behavior: Missing field defaults to None in reconfigure defaults.
  redundancy: Defaults behavior repeated across element flows.
  decision_rationale: Combine into shared defaults tests.
---

# Behavior summary

Missing optional field shows None default.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate defaults behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating defaults tests.

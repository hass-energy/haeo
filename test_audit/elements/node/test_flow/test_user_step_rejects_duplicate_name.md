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
  nodeid: tests/elements/node/test_flow.py::test_user_step_rejects_duplicate_name
  source_file: tests/elements/node/test_flow.py
  test_class: ''
  test_function: test_user_step_rejects_duplicate_name
  fixtures: []
  markers: []
notes:
  behavior: Duplicate names rejected in user flow.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared validation tests.
---

# Behavior summary

Duplicate names yield validation error.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate duplicate-name behavior.

# Fixtures / setup

Uses hub entry with existing subentry.

# Next actions

Consider consolidating duplicate-name tests.

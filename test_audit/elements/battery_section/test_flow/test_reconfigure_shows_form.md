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
  nodeid: tests/elements/battery_section/test_flow.py::test_reconfigure_shows_form
  source_file: tests/elements/battery_section/test_flow.py
  test_class: ''
  test_function: test_reconfigure_shows_form
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure shows form for existing subentry.
  redundancy: Repeated across element flow tests.
  decision_rationale: Combine into shared reconfigure behavior tests.
---

# Behavior summary

Reconfigure step returns a form with current values.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared reconfigure behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating into shared flow test.

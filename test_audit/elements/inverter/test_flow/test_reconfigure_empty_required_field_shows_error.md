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
  nodeid: tests/elements/inverter/test_flow.py::test_reconfigure_empty_required_field_shows_error
  source_file: tests/elements/inverter/test_flow.py
  test_class: ''
  test_function: test_reconfigure_empty_required_field_shows_error
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure errors on empty required fields.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared validation tests.
---

# Behavior summary

Empty required inputs yield validation errors during reconfigure.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate validation behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating validation tests.

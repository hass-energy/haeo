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
  nodeid: tests/elements/node/test_flow.py::test_reconfigure_step_shows_form_initially
  source_file: tests/elements/node/test_flow.py
  test_class: ''
  test_function: test_reconfigure_step_shows_form_initially
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure without input shows form with defaults.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared defaults tests.
---

# Behavior summary

Reconfigure returns form with existing defaults.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate defaults behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating defaults tests.

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
  nodeid: tests/elements/node/test_flow.py::test_user_step_shows_form_initially
  source_file: tests/elements/node/test_flow.py
  test_class: ''
  test_function: test_user_step_shows_form_initially
  fixtures: []
  markers: []
notes:
  behavior: User step with no input returns form.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared flow tests.
---

# Behavior summary

User step returns initial form when no input provided.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared flow behavior.

# Fixtures / setup

Uses hub entry.

# Next actions

Consider consolidating flow tests.

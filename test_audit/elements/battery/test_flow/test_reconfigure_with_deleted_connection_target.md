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
  nodeid: tests/elements/battery/test_flow.py::test_reconfigure_with_deleted_connection_target
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_deleted_connection_target
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure flow includes deleted connection target in options.
  redundancy: Pattern repeated across element flow tests.
  decision_rationale: Combine into shared flow behavior tests.
---

# Behavior summary

Reconfigure preserves deleted connection targets for selection.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared flow behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating into shared flow test.

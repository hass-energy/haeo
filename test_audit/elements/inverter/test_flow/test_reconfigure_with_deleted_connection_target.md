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
  nodeid: tests/elements/inverter/test_flow.py::test_reconfigure_with_deleted_connection_target
  source_file: tests/elements/inverter/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_deleted_connection_target
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure tolerates deleted connection targets.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared reconfigure behavior tests.
---

# Behavior summary

Deleted connection targets are preserved in reconfigure.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared flow behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating into shared flow test.

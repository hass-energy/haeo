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
  nodeid: tests/elements/connection/test_flow.py::test_reconfigure_with_deleted_participant
  source_file: tests/elements/connection/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_deleted_participant
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure shows form even when a participant was deleted.
  redundancy: Pattern repeated across element flows.
  decision_rationale: Combine into shared reconfigure behavior tests.
---

# Behavior summary

Deleted participants are tolerated in reconfigure.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared flow behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating into shared flow test.

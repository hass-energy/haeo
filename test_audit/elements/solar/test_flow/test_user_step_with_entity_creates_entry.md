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
  nodeid: tests/elements/solar/test_flow.py::test_user_step_with_entity_creates_entry
  source_file: tests/elements/solar/test_flow.py
  test_class: ''
  test_function: test_user_step_with_entity_creates_entry
  fixtures: []
  markers: []
notes:
  behavior: User flow with entity values creates entry storing entity IDs.
  redundancy: Core solar flow behavior.
  decision_rationale: Keep. Validates entity ID handling.
---

# Behavior summary

Entity selections are stored as schema entity IDs in created entry.

# Redundancy / overlap

Distinct from constant-value user flow test.

# Decision rationale

Keep. Entity ID handling should be validated.

# Fixtures / setup

Uses hub entry and participant setup.

# Next actions

None.

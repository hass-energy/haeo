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
  nodeid: tests/elements/battery/test_flow.py::test_user_step_with_entity_values_creates_entry
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_user_step_with_entity_values_creates_entry
  fixtures: []
  markers: []
notes:
  behavior: User flow with entity values creates entry with entity IDs.
  redundancy: Core battery flow behavior.
  decision_rationale: Keep. Ensures entity values are stored correctly.
---

# Behavior summary

Entity selections are stored as schema entity IDs in created entry.

# Redundancy / overlap

Distinct from constant-value user flow test.

# Decision rationale

Keep. Validates entity ID handling.

# Fixtures / setup

Uses hub entry and participant setup.

# Next actions

None.

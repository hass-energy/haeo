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
  nodeid: tests/elements/inverter/test_flow.py::test_reconfigure_selecting_entity_stores_entity_id
  source_file: tests/elements/inverter/test_flow.py
  test_class: ''
  test_function: test_reconfigure_selecting_entity_stores_entity_id
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure selection stores chosen entity IDs.
  redundancy: Distinct entity registry selection behavior.
  decision_rationale: Keep. Entity selection persistence is important.
---

# Behavior summary

Selected entity IDs are stored during reconfigure.

# Redundancy / overlap

No overlap with defaults tests.

# Decision rationale

Keep. Ensures entity selection persistence.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

None.

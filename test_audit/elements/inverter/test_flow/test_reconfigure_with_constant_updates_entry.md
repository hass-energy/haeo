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
  nodeid: tests/elements/inverter/test_flow.py::test_reconfigure_with_constant_updates_entry
  source_file: tests/elements/inverter/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_constant_updates_entry
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure updates entry with constant values.
  redundancy: Core reconfigure update behavior.
  decision_rationale: Keep. Reconfigure updates are important.
---

# Behavior summary

Reconfigure persists updated constant values.

# Redundancy / overlap

Similar to reconfigure update tests in other elements.

# Decision rationale

Keep. Reconfigure update should be validated.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

None.

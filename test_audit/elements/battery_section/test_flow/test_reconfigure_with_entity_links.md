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
  nodeid: tests/elements/battery_section/test_flow.py::test_reconfigure_with_entity_links
  source_file: tests/elements/battery_section/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_entity_links
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure handles entity link schema values.
  redundancy: Repeated across element flow tests.
  decision_rationale: Combine into shared reconfigure behavior tests.
---

# Behavior summary

Reconfigure preserves entity link schema values.

# Redundancy / overlap

Repeated across multiple element flow tests.

# Decision rationale

Combine. Consolidate shared reconfigure behavior.

# Fixtures / setup

Uses hub entry and subentry.

# Next actions

Consider consolidating into shared flow test.

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
  nodeid: tests/elements/battery/test_flow.py::test_reconfigure_partition_defaults_entity_links
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_reconfigure_partition_defaults_entity_links
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure defaults show entity links for partition fields.
  redundancy: Battery-specific partition defaults.
  decision_rationale: Keep. Ensures entity defaults are shown.
---

# Behavior summary

Partition reconfigure defaults include entity links.

# Redundancy / overlap

Distinct from scalar partition defaults.

# Decision rationale

Keep. Partition defaults behavior should be validated.

# Fixtures / setup

Uses hub entry and existing subentry.

# Next actions

None.

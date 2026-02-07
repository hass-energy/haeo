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
  nodeid: tests/elements/battery/test_flow.py::test_partition_flow_with_constant_values_creates_entry
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_partition_flow_with_constant_values_creates_entry
  fixtures: []
  markers: []
notes:
  behavior: Partition flow creates entry with constant partition values.
  redundancy: Battery-specific partition behavior.
  decision_rationale: Keep. Ensures partition constants are stored.
---

# Behavior summary

Partition constants are persisted when completing partition flow.

# Redundancy / overlap

Distinct from partition entity-link test.

# Decision rationale

Keep. Partition constant handling is important.

# Fixtures / setup

Uses hub entry and participant setup.

# Next actions

None.

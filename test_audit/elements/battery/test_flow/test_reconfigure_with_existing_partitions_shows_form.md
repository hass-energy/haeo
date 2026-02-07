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
  nodeid: tests/elements/battery/test_flow.py::test_reconfigure_with_existing_partitions_shows_form
  source_file: tests/elements/battery/test_flow.py
  test_class: ''
  test_function: test_reconfigure_with_existing_partitions_shows_form
  fixtures: []
  markers: []
notes:
  behavior: Reconfigure shows partition form when partitions exist.
  redundancy: Battery-specific partition reconfigure behavior.
  decision_rationale: Keep. Partition reconfigure is important.
---

# Behavior summary

Existing partitions trigger the partition reconfigure form.

# Redundancy / overlap

Distinct from non-partition reconfigure tests.

# Decision rationale

Keep. Partition reconfigure behavior should be validated.

# Fixtures / setup

Uses hub entry and existing subentry.

# Next actions

None.

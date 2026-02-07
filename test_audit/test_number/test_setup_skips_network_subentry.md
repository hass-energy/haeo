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
  nodeid: tests/test_number.py::test_setup_skips_network_subentry
  source_file: tests/test_number.py
  test_class: ''
  test_function: test_setup_skips_network_subentry
  fixtures: []
  markers: []
notes:
  behavior: Ensures network-only subentries do not create number entities.
  redundancy: Unique network-only behavior.
  decision_rationale: Keep. Validates skip logic for network subentry.
---

# Behavior summary

Asserts a network-only subentry does not yield number entities.

# Redundancy / overlap

No overlap with element-based number creation tests.

# Decision rationale

Keep. Network subentry should not create numbers.

# Fixtures / setup

Uses Home Assistant fixtures.

# Next actions

None.

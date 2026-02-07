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
  nodeid: tests/test_switch.py::test_setup_skips_element_without_switch_fields
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_skips_element_without_switch_fields
  fixtures: []
  markers: []
notes:
  behavior: Ensures elements without switch fields do not create switch entities.
  redundancy: Overlaps with network-only setup case; can be folded into a broader setup test.
  decision_rationale: Combine with the network-only setup test if consolidating.
---

# Behavior summary

Asserts that non-switch elements are skipped during switch setup.

# Redundancy / overlap

Partial overlap with network switch creation test.

# Decision rationale

Combine. These can be validated within a single setup test.

# Fixtures / setup

Uses Home Assistant fixtures and mock subentries.

# Next actions

Consider merging into `test_setup_creates_auto_optimize_switch_for_network`.

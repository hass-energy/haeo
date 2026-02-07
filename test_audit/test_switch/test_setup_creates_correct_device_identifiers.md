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
  nodeid: tests/test_switch.py::test_setup_creates_correct_device_identifiers
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_creates_correct_device_identifiers
  fixtures: []
  markers: []
notes:
  behavior: Ensures created switch entities include correct device identifiers.
  redundancy: Distinct device metadata check; could be folded into another setup test.
  decision_rationale: Keep. Device registry metadata is important.
---

# Behavior summary

Asserts created switch entities carry expected device identifiers.

# Redundancy / overlap

Could be combined with curtailment switch creation test.

# Decision rationale

Keep. Validates device metadata.

# Fixtures / setup

Uses Home Assistant fixtures and mock subentries.

# Next actions

None.

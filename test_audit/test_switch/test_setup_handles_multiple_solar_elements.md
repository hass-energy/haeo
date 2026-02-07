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
  nodeid: tests/test_switch.py::test_setup_handles_multiple_solar_elements
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_handles_multiple_solar_elements
  fixtures: []
  markers: []
notes:
  behavior: Creates switch entities for multiple solar subentries.
  redundancy: Overlaps with curtailment setup; adds multi-subentry coverage.
  decision_rationale: Keep. Multi-subentry handling is useful.
---

# Behavior summary

Ensures multiple solar subentries yield corresponding switch entities.

# Redundancy / overlap

Some overlap with single-subentry curtailment setup.

# Decision rationale

Keep. Ensures setup scales across subentries.

# Fixtures / setup

Uses Home Assistant fixtures and multiple solar subentries.

# Next actions

Consider strengthening assertions to verify all expected names.

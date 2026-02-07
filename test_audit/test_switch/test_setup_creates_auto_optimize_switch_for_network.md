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
  nodeid: tests/test_switch.py::test_setup_creates_auto_optimize_switch_for_network
  source_file: tests/test_switch.py
  test_class: ''
  test_function: test_setup_creates_auto_optimize_switch_for_network
  fixtures: []
  markers: []
notes:
  behavior: Creates the Auto Optimize switch for the network subentry.
  redundancy: Base network switch setup case; minimal overlap.
  decision_rationale: Keep. Confirms network-level switch creation.
---

# Behavior summary

Verifies a single Auto Optimize switch entity is created for the network subentry.

# Redundancy / overlap

Limited overlap with other setup tests; this is the network-only case.

# Decision rationale

Keep. Network switch is a core entity.

# Fixtures / setup

Uses Home Assistant fixtures and a mock config entry.

# Next actions

None.

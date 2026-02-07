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
  nodeid: tests/test_diagnostics.py::test_diagnostics_skips_network_subentry
  source_file: tests/test_diagnostics.py
  test_class: ''
  test_function: test_diagnostics_skips_network_subentry
  fixtures: []
  markers: []
notes:
  behavior: Skips network subentry for participants and input collection.
  redundancy: Distinct from invalid config test.
  decision_rationale: Keep. Validates network subentry exclusion.
---

# Behavior summary

Ensures network subentries are not included in participants or inputs diagnostics.

# Redundancy / overlap

No overlap with invalid-config test.

# Decision rationale

Keep. Network subentry should be excluded.

# Fixtures / setup

Uses Home Assistant fixtures and mock subentries.

# Next actions

None.

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
  nodeid: tests/test_network.py::test_evaluate_network_connectivity_resolves_issue
  source_file: tests/test_network.py
  test_class: ''
  test_function: test_evaluate_network_connectivity_resolves_issue
  fixtures: []
  markers: []
notes:
  behavior: Clears the disconnected-network issue once connectivity is restored.
  redundancy: Shares setup with disconnected test but uniquely covers issue resolution.
  decision_rationale: Keep. Validates issue resolution lifecycle.
---

# Behavior summary

Creates a disconnected network issue, adds a connection, re-evaluates, and asserts the issue is cleared.

# Redundancy / overlap

No overlap with disconnected case; this validates resolution.

# Decision rationale

Keep. Ensures issue cleanup when connectivity is restored.

# Fixtures / setup

Uses `config_entry` fixture.

# Next actions

None.

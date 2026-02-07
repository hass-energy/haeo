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
  nodeid: tests/test_network.py::test_evaluate_network_connectivity_connected
  source_file: tests/test_network.py
  test_class: ''
  test_function: test_evaluate_network_connectivity_connected
  fixtures: []
  markers: []
notes:
  behavior: Ensures a single-node network is treated as connected and no repair issue is created.
  redundancy: Distinct no-issue case; complements disconnected tests.
  decision_rationale: Keep. Validates connected-network baseline.
---

# Behavior summary

Runs connectivity evaluation with one node and asserts no issue is created.

# Redundancy / overlap

No overlap with disconnected or resolution cases.

# Decision rationale

Keep. Connected case is required for baseline behavior.

# Fixtures / setup

Uses `config_entry` fixture.

# Next actions

None.

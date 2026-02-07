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
  nodeid: tests/test_network.py::test_evaluate_network_connectivity_disconnected
  source_file: tests/test_network.py
  test_class: ''
  test_function: test_evaluate_network_connectivity_disconnected
  fixtures: []
  markers: []
notes:
  behavior: Creates a repair issue when nodes are disconnected and asserts the translation key.
  redundancy: Overlaps with resolution test setup but adds explicit translation key assertion.
  decision_rationale: Keep. Validates issue creation and translation key.
---

# Behavior summary

Evaluates connectivity with two isolated nodes and asserts a disconnected_network issue is created.

# Redundancy / overlap

Shared setup with resolution test but different assertions.

# Decision rationale

Keep. Covers issue creation behavior.

# Fixtures / setup

Uses `config_entry` fixture.

# Next actions

None.

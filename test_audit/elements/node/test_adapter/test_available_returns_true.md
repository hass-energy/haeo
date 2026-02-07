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
  nodeid: tests/elements/node/test_adapter.py::test_available_returns_true
  source_file: tests/elements/node/test_adapter.py
  test_class: ''
  test_function: test_available_returns_true
  fixtures: []
  markers: []
notes:
  behavior: Availability returns true because nodes have no sensor dependencies.
  redundancy: Unique for node elements.
  decision_rationale: Keep. Confirms node availability behavior.
---

# Behavior summary

Nodes are always available regardless of sensors.

# Redundancy / overlap

Distinct from sensor-dependent element availability tests.

# Decision rationale

Keep. Ensures node availability rule.

# Fixtures / setup

Uses hass instance.

# Next actions

None.

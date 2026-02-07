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
  nodeid: tests/test_data_loading.py::test_create_network_sorts_connections_after_elements
  source_file: tests/test_data_loading.py
  test_class: ''
  test_function: test_create_network_sorts_connections_after_elements
  fixtures: []
  markers: []
notes:
  behavior: Ensures connections are added after node elements regardless of input order.
  redundancy: Unique ordering behavior coverage.
  decision_rationale: Keep. Ordering is important for network building.
---

# Behavior summary

Validates create_network sorts elements so connections are added after nodes.

# Redundancy / overlap

No overlap with other network creation tests.

# Decision rationale

Keep. Ensures correct build order.

# Fixtures / setup

Uses Home Assistant fixtures and mock participants.

# Next actions

None.
